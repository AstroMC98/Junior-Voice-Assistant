import asyncio
import uuid

from knowledge_base.ingestion.phase_runner import run_phase
from knowledge_base.ingestion.agents.page_segmenter import PageSegmenter
from knowledge_base.ingestion.agents.document_classifier import DocumentClassifier
from knowledge_base.ingestion.agents.chunk_classifier import ChunkClassifier
from knowledge_base.ingestion.agents.image_classifier import ImageClassifier
from knowledge_base.ingestion.agents.type_specific_extractor import TypeSpecificExtractor
from knowledge_base.ingestion.agents.diagram_analyzer import DiagramAnalyzer
from knowledge_base.ingestion.agents.reference_image_processor import ReferenceImageProcessor
from knowledge_base.ingestion.agents.positional_analyzer import PositionalAnalyzer
from knowledge_base.ingestion.agents.vernacular_generator import VernacularGenerator
from knowledge_base.ingestion.agents.module_assembler import ModuleAssembler
from knowledge_base.ingestion.agents.reference_linker import ReferenceLinker
from knowledge_base.ingestion.agents.quality_checker import QualityChecker
from knowledge_base.store.knowledge_store import KnowledgeStore


async def ingest_document(pdf_path: str, store: KnowledgeStore) -> dict:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        pages = [doc[i].get_pixmap().tobytes("png") for i in range(len(doc))]
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF ingestion: pip install pymupdf")

    trace_id = str(uuid.uuid4())

    # Phase 1: Segmentation (parallel per page) + DocumentClassifier (parallel)
    segmenter = PageSegmenter()
    classifier = DocumentClassifier()
    seg_results, doc_class = await asyncio.gather(
        run_phase([segmenter.segment(p, i) for i, p in enumerate(pages)]),
        classifier.classify(pages[:3]),
    )
    doc_type = doc_class.get("document_type", "general")

    # Phase 2: Classification (parallel per chunk/image)
    chunk_clf = ChunkClassifier()
    img_clf = ImageClassifier()
    all_chunks = [
        (r["text"], doc_type)
        for seg in seg_results
        for r in seg.text_regions
    ]
    all_image_hints = [
        r.get("role_hint")
        for seg in seg_results
        for r in seg.image_regions
    ]

    chunk_types, img_roles = await asyncio.gather(
        run_phase([chunk_clf.classify(text, bias) for text, bias in all_chunks]),
        run_phase([img_clf.classify_role(hint) for hint in all_image_hints]),
    )

    # Phase 3: Text extraction (parallel)
    extractor = TypeSpecificExtractor()
    structured_results = await run_phase([
        extractor.extract(text, ct.get("entry_type", "narrative"))
        for (text, _), ct in zip(all_chunks, chunk_types)
    ])

    # Phase 4: Assembly + Vernacular (sequential per entry due to mutable state)
    assembler = ModuleAssembler()
    vernacular_gen = VernacularGenerator()
    entries = []
    for (text, _), ct, sd in zip(all_chunks, chunk_types, structured_results):
        entry = assembler.assemble(
            source_document=pdf_path,
            entry_type=ct.get("entry_type", "narrative"),
            raw_text=text,
            structured_data=sd,
            image_results=[],
            ingestion_trace_id=trace_id,
            confidence_score=ct.get("confidence", 0.8),
        )
        terms = await vernacular_gen.generate(entry.title, entry.summary, entry.tags)
        entry.vernacular_terms = terms
        entries.append(entry)

    # Phase 5: Linking + Quality check
    linker = ReferenceLinker()
    checker = QualityChecker()
    entries = linker.link(entries)
    reports = [checker.check(e) for e in entries]

    # Phase 6: Storage
    for entry in entries:
        await store.save(entry)

    return {
        "trace_id": trace_id,
        "document_type": doc_type,
        "entries_created": len(entries),
        "requires_review": sum(1 for r in reports if r.requires_review),
    }
