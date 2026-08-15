import json
from pathlib import Path

from pydantic import ValidationError

from app.ai.provider import LLMProvider, LLMResult
from app.schemas.reflection import ReflectionOutput

PROMPT_VERSION = "reflection_v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.txt"


def build_prompt(diary_content: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{diary_content}", diary_content)


async def generate_reflection(
    diary_content: str,
    provider: LLMProvider,
) -> tuple[ReflectionOutput, LLMResult]:
    result = await provider.generate(build_prompt(diary_content))
    try:
        parsed = ReflectionOutput.model_validate(json.loads(result.content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("invalid structured LLM output") from exc
    return parsed, result
