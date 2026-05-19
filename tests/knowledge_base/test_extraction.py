import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_base.ingestion.agents.type_specific_extractor import TypeSpecificExtractor


@pytest.mark.asyncio
async def test_extract_decision_tree():
    mock_json = '{"conditions": ["serial ends in even"], "branches": [{"condition": "yes", "action": "cut"}], "outcomes": ["cut", "dont_cut"], "default": "dont_cut"}'
    mock_response = MagicMock()
    mock_response.text = mock_json
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.run_llm",
               AsyncMock(return_value=mock_response)):
        extractor = TypeSpecificExtractor()
        result = await extractor.extract(
            text="If the last digit of the serial number is even, cut the wire. Otherwise, don't.",
            entry_type="decision_tree"
        )
    assert "conditions" in result
    assert "branches" in result


@pytest.mark.asyncio
async def test_extract_procedure():
    mock_json = '{"steps": [{"order": 1, "action": "Note the wire colors", "note": null}], "prerequisites": [], "warnings": ["Order matters"]}'
    mock_response = MagicMock()
    mock_response.text = mock_json
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.run_llm",
               AsyncMock(return_value=mock_response)):
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("Step 1: note colors", "procedure")
    assert "steps" in result
    assert len(result["steps"]) == 1


@pytest.mark.asyncio
async def test_extract_strips_markdown_fences():
    mock_text = '```json\n{"steps": [], "prerequisites": [], "warnings": []}\n```'
    mock_response = MagicMock()
    mock_response.text = mock_text
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.run_llm",
               AsyncMock(return_value=mock_response)):
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("some text", "procedure")
    assert "steps" in result


@pytest.mark.asyncio
async def test_extract_reference_table():
    mock_json = '{"columns": ["Letter", "Morse"], "rows": [["A", ".-"], ["B", "-..."]], "lookup_keys": ["Letter"]}'
    mock_response = MagicMock()
    mock_response.text = mock_json
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.run_llm",
               AsyncMock(return_value=mock_response)):
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("A = .-, B = -...", "reference_table")
    assert result["columns"] == ["Letter", "Morse"]


@pytest.mark.asyncio
async def test_extract_unknown_type_uses_generic_prompt():
    mock_json = '{"key": "value"}'
    mock_response = MagicMock()
    mock_response.text = mock_json
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.run_llm",
               AsyncMock(return_value=mock_response)):
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("some text", "unknown_type")
    assert isinstance(result, dict)


from knowledge_base.ingestion.agents.diagram_analyzer import DiagramAnalyzer


@pytest.mark.asyncio
async def test_diagram_analyzer_venn_extraction():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "type": "venn_logic",
        "dimensions": ["has_red", "has_blue", "has_star", "led_on"],
        "regions": [
            {"conditions": {"has_red": False, "has_blue": False, "has_star": False, "led_on": False}, "action": "C"},
            {"conditions": {"has_red": True, "has_blue": False, "has_star": False, "led_on": False}, "action": "S"},
        ],
        "action_legend": {"C": "Cut the wire", "S": "Cut if serial even"},
        "extraction_confidence": 0.85,
        "raw_description": "Four-set Venn diagram...",
    }
    with patch("knowledge_base.ingestion.agents.diagram_analyzer.generate_with_image",
               AsyncMock(return_value=mock_response)):
        analyzer = DiagramAnalyzer()
        result = await analyzer.analyze(image=b"png_bytes")
    assert result["type"] == "venn_logic"
    assert len(result["dimensions"]) == 4
    assert len(result["regions"]) == 2
    assert result["extraction_confidence"] == 0.85


@pytest.mark.asyncio
async def test_diagram_analyzer_is_high_confidence():
    analyzer = DiagramAnalyzer()
    assert analyzer.is_high_confidence({"extraction_confidence": 0.85}) is True
    assert analyzer.is_high_confidence({"extraction_confidence": 0.65}) is False
    assert analyzer.is_high_confidence({"extraction_confidence": 0.70}) is True
    assert analyzer.is_high_confidence({}) is False


@pytest.mark.asyncio
async def test_diagram_analyzer_returns_parsed_result():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "type": "flowchart", "dimensions": [], "regions": [],
        "action_legend": {}, "extraction_confidence": 0.9, "raw_description": "x",
    }
    with patch("knowledge_base.ingestion.agents.diagram_analyzer.generate_with_image",
               AsyncMock(return_value=mock_response)):
        analyzer = DiagramAnalyzer()
        result = await analyzer.analyze(b"img")
    assert result["type"] == "flowchart"


from knowledge_base.ingestion.agents.reference_image_processor import ReferenceImageProcessor


@pytest.mark.asyncio
async def test_reference_image_processor_multi_level():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "technical": "DB-25 parallel port, 25 pins in two rows (13/12)",
        "layperson": "wide rectangular connector with two rows of small holes",
        "distinguishing_features": [
            "widest connector type on the bomb",
            "two rows: 13 top, 12 bottom",
        ],
        "commonly_confused_with": ["serial_port", "dvi_d"],
        "differentiators": {
            "vs_serial_port": "parallel is much wider with more holes",
            "vs_dvi_d": "parallel has round holes; DVI-D has a flat rectangular pin cluster",
        },
    }
    with patch("knowledge_base.ingestion.agents.reference_image_processor.generate_with_image",
               AsyncMock(return_value=mock_response)):
        proc = ReferenceImageProcessor()
        result = await proc.process(image=b"png_data")
    assert "technical" in result
    assert "layperson" in result
    assert "distinguishing_features" in result
    assert len(result["distinguishing_features"]) == 2
    assert "differentiators" in result


from knowledge_base.ingestion.agents.positional_analyzer import PositionalAnalyzer


@pytest.mark.asyncio
async def test_positional_analyzer_grid():
    mock_response = MagicMock()
    mock_response.parsed.model_dump.return_value = {
        "coordinate_system": "grid",
        "positions": {
            "A1": "YES", "A2": "NO", "A3": "THEY ARE",
            "B1": "UH HUH", "B2": "FIRST", "B3": "THIS",
        },
        "mappings": {
            "top-left": "A1", "top-center": "A2",
        },
    }
    with patch("knowledge_base.ingestion.agents.positional_analyzer.generate_with_image",
               AsyncMock(return_value=mock_response)):
        analyzer = PositionalAnalyzer()
        result = await analyzer.analyze(image=b"grid_png")
    assert result["coordinate_system"] == "grid"
    assert "A1" in result["positions"]
    assert result["positions"]["A1"] == "YES"
