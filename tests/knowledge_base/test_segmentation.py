import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_base.ingestion.phase_runner import run_phase


@pytest.mark.asyncio
async def test_run_phase_executes_all():
    results = []

    async def work(i):
        await asyncio.sleep(0)
        results.append(i)
        return i * 2

    output = await run_phase([work(i) for i in range(5)], max_concurrency=3)
    assert sorted(output) == [0, 2, 4, 6, 8]
    assert sorted(results) == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_run_phase_respects_concurrency():
    active = []
    peak = []

    async def work(i):
        active.append(i)
        peak.append(len(active))
        await asyncio.sleep(0.01)
        active.remove(i)
        return i

    await run_phase([work(i) for i in range(10)], max_concurrency=3)
    assert max(peak) <= 3


@pytest.mark.asyncio
async def test_run_phase_propagates_exceptions():
    async def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await run_phase([failing()])


@pytest.mark.asyncio
async def test_run_phase_empty_list():
    result = await run_phase([])
    assert result == []


from knowledge_base.ingestion.agents.page_segmenter import PageSegmenter, SegmentationResult
from knowledge_base.prompts.ingestion.page_segmenter import (
    PageSegmenterOutput, TextRegion, ImageRegion,
)


@pytest.mark.asyncio
async def test_page_segmenter_returns_text_and_image_regions():
    mock_response = MagicMock()
    mock_response.parsed = PageSegmenterOutput(
        text_regions=[TextRegion(bbox=[0, 0, 595, 100], text="Cut the red wire", confidence=0.95)],
        image_regions=[ImageRegion(bbox=[0, 100, 595, 300], role_hint="diagram")],
    )
    with patch("knowledge_base.ingestion.agents.page_segmenter.generate_with_image",
               AsyncMock(return_value=mock_response)):
        seg = PageSegmenter()
        result = await seg.segment(page_image=b"fake_png_bytes", page_number=3)

    assert isinstance(result, SegmentationResult)
    assert result.page_number == 3
    assert len(result.text_regions) == 1
    assert result.text_regions[0]["text"] == "Cut the red wire"
    assert len(result.image_regions) == 1
    assert result.image_regions[0]["role_hint"] == "diagram"


@pytest.mark.asyncio
async def test_page_segmenter_handles_empty_page():
    mock_response = MagicMock()
    mock_response.parsed = PageSegmenterOutput(text_regions=[], image_regions=[])
    with patch("knowledge_base.ingestion.agents.page_segmenter.generate_with_image",
               AsyncMock(return_value=mock_response)):
        seg = PageSegmenter()
        result = await seg.segment(b"blank", 0)
    assert result.text_regions == []
    assert result.image_regions == []


from knowledge_base.ingestion.agents.document_classifier import DocumentClassifier


@pytest.mark.asyncio
async def test_document_classifier_returns_type():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "document_type": "game_manual", "confidence": 0.92,
        "reasoning": "Contains module defusal instructions",
    }
    with patch("knowledge_base.ingestion.agents.document_classifier.generate_with_images",
               AsyncMock(return_value=mock_response)):
        clf = DocumentClassifier()
        result = await clf.classify(first_pages=[b"page1_png", b"page2_png"])
    assert result["document_type"] == "game_manual"
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_document_classifier_limits_to_3_pages():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "document_type": "recipe", "confidence": 0.88, "reasoning": "Contains ingredients",
    }
    with patch("knowledge_base.ingestion.agents.document_classifier.generate_with_images",
               AsyncMock(return_value=mock_response)) as mock_gen:
        clf = DocumentClassifier()
        await clf.classify(first_pages=[b"p"] * 10)
    images_sent = mock_gen.call_args.args[1]
    assert len(images_sent) == 3


from knowledge_base.ingestion.agents.chunk_classifier import ChunkClassifier
from knowledge_base.ingestion.agents.image_classifier import ImageClassifier


@pytest.mark.asyncio
async def test_chunk_classifier_returns_entry_type():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {"entry_type": "decision_tree", "confidence": 0.88}
    with patch("knowledge_base.ingestion.agents.chunk_classifier.run_llm",
               AsyncMock(return_value=mock_response)):
        clf = ChunkClassifier()
        result = await clf.classify(
            text="If the last digit of serial is even, cut the red wire.",
            document_type_bias="game_manual"
        )
    assert result["entry_type"] == "decision_tree"
    assert result["confidence"] == 0.88


@pytest.mark.asyncio
async def test_image_classifier_returns_role():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {"role": "logic_diagram", "confidence": 0.91}
    with patch("knowledge_base.ingestion.agents.image_classifier.generate_with_image",
               AsyncMock(return_value=mock_response)):
        clf = ImageClassifier()
        result = await clf.classify_role(role_hint="diagram", image_bytes=b"png_data")
    assert result["role"] == "logic_diagram"
