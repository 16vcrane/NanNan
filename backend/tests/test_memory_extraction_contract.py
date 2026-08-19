import pytest
from pydantic import ValidationError

from app.ai.memory_extraction import EvidenceValidationError, validate_evidence_spans
from app.schemas.memory_extraction import MemoryExtractionOutput


def test_memory_extraction_evidence_must_match_source() -> None:
    content = "今天终于完成了毕业答辩。"
    output = MemoryExtractionOutput.model_validate(
        {
            "items": [
                {
                    "type": "achievement",
                    "label": "完成毕业答辩",
                    "normalizedValue": "毕业答辩",
                    "evidence": "完成了毕业答辩",
                    "startOffset": 4,
                    "endOffset": 11,
                    "confidence": 0.96,
                    "occurredOn": None,
                    "attributes": {},
                }
            ]
        }
    )

    validated = validate_evidence_spans(content, output)

    assert validated.items[0].evidence == "完成了毕业答辩"


def test_memory_extraction_rejects_invalid_evidence_offsets() -> None:
    output = MemoryExtractionOutput.model_validate(
        {
            "items": [
                {
                    "type": "event",
                    "label": "开会",
                    "normalizedValue": "开会",
                    "evidence": "开会",
                    "startOffset": 0,
                    "endOffset": 2,
                    "confidence": 0.9,
                    "occurredOn": None,
                    "attributes": {},
                }
            ]
        }
    )

    with pytest.raises(EvidenceValidationError):
        validate_evidence_spans("今天没有开会。", output)


def test_memory_extraction_schema_rejects_unknown_types() -> None:
    with pytest.raises(ValidationError):
        MemoryExtractionOutput.model_validate(
            {
                "items": [
                    {
                        "type": "diagnosis",
                        "label": "焦虑",
                        "normalizedValue": "焦虑",
                        "evidence": "我有点焦虑",
                        "startOffset": 0,
                        "endOffset": 5,
                        "confidence": 0.9,
                        "occurredOn": None,
                        "attributes": {},
                    }
                ]
            }
        )


def test_memory_extraction_filters_sensitive_inference_candidates() -> None:
    content = "最近总是睡不好。"
    output = MemoryExtractionOutput.model_validate(
        {
            "items": [
                {
                    "type": "event",
                    "label": "焦虑",
                    "normalizedValue": "焦虑",
                    "evidence": "睡不好",
                    "startOffset": 4,
                    "endOffset": 7,
                    "confidence": 0.9,
                    "occurredOn": None,
                    "attributes": {},
                }
            ]
        }
    )

    assert validate_evidence_spans(content, output).items == []
