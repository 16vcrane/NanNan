import json
from pathlib import Path

from pydantic import ValidationError

from app.ai.provider import LLMProvider, LLMResult
from app.schemas.memory_extraction import MemoryExtractionOutput

PROMPT_VERSION = "memory_extract_v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.txt"
SENSITIVE_INFERENCE_TERMS = (
    "疾病",
    "抑郁",
    "焦虑",
    "人格",
    "政治倾向",
    "收入",
)


class EvidenceValidationError(ValueError):
    pass


def build_prompt(diary_content: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{diary_content}", diary_content)


def validate_evidence_spans(
    diary_content: str,
    output: MemoryExtractionOutput,
) -> MemoryExtractionOutput:
    valid_items = []
    for item in output.items:
        if item.end_offset > len(diary_content) or item.start_offset >= item.end_offset:
            raise EvidenceValidationError("evidence offsets are outside the diary content")
        if diary_content[item.start_offset:item.end_offset] != item.evidence:
            raise EvidenceValidationError("evidence text does not match the diary content")
        if any(term in item.label or term in item.normalized_value for term in SENSITIVE_INFERENCE_TERMS):
            continue
        valid_items.append(item)
    return MemoryExtractionOutput(items=valid_items)


async def extract_memories(
    diary_content: str,
    provider: LLMProvider,
) -> tuple[MemoryExtractionOutput, LLMResult]:
    result = await provider.generate(build_prompt(diary_content))
    try:
        parsed = MemoryExtractionOutput.model_validate(json.loads(result.content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("invalid structured memory extraction output") from exc
    return validate_evidence_spans(diary_content, parsed), result
