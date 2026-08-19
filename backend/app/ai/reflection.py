import json
from pathlib import Path

from pydantic import ValidationError

from app.ai.provider import LLMProvider, LLMResult
from app.schemas.reflection import ReflectionOutput

PROMPT_VERSION = "reflection_v1"
REFLECTION_V2_VERSION = "reflection_v2"


def build_prompt(diary_content: str) -> str:
    template = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.txt").read_text(encoding="utf-8")
    return template.replace("{diary_content}", diary_content)


def build_memory_prompt(diary_content: str, memory_context: str) -> str:
    template = (Path(__file__).parent / "prompts" / f"{REFLECTION_V2_VERSION}.txt").read_text(encoding="utf-8")
    return template.replace("{diary_content}", diary_content).replace("{memory_context}", memory_context)


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


async def generate_memory_reflection(
    diary_content: str,
    memory_context: str,
    provider: LLMProvider,
) -> tuple[ReflectionOutput, LLMResult]:
    result = await provider.generate(build_memory_prompt(diary_content, memory_context))
    try:
        parsed = ReflectionOutput.model_validate(json.loads(result.content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("invalid structured LLM output") from exc
    return parsed, result
