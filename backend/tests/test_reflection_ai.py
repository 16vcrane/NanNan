import json

import pytest

from app.ai.guardrails import (
    OutputGuardrailError,
    check_input,
    validate_output,
)
from app.ai.provider import LLMProvider, LLMResult
from app.ai.reflection import PROMPT_VERSION, generate_reflection


class FakeProvider(LLMProvider):
    def __init__(self, payload: dict):
        self.payload = payload
        self.prompt = ""

    async def generate(self, prompt: str) -> LLMResult:
        self.prompt = prompt
        return LLMResult(
            content=json.dumps(self.payload, ensure_ascii=False),
            model_name="fake-model",
            token_usage=42,
        )


@pytest.mark.asyncio
async def test_structured_reflection_output_and_versioned_prompt() -> None:
    reflection = "你今天完成了项目里重要的一步，也把这份认真清楚地留在了这一页。愿这份踏实陪你安稳走过今晚。"
    provider = FakeProvider(
        {"reflection": reflection, "keywords": ["项目", "完成"], "tone": "warm"}
    )

    output, result = await generate_reflection("今天完成了项目的重要一步。", provider)

    assert output.reflection == reflection
    assert result.model_name == "fake-model"
    assert "今天完成了项目的重要一步。" in provider.prompt
    assert PROMPT_VERSION == "reflection_v1"


@pytest.mark.asyncio
async def test_invalid_structured_output_is_rejected() -> None:
    provider = FakeProvider(
        {"reflection": "太短", "keywords": [], "tone": "warm"}
    )
    with pytest.raises(ValueError, match="invalid structured LLM output"):
        await generate_reflection("今天完成了项目。", provider)


def test_input_crisis_is_blocked_before_provider() -> None:
    result = check_input("我不想活了，也不知道该怎么办。")
    assert result.safe is False
    assert result.safety_status == "sensitive"


def test_guardrail_accepts_specific_safe_output() -> None:
    diary = "今天下班路上买了一杯热咖啡，觉得放松了一点。"
    output = "你在下班路上遇见的那杯热咖啡，让忙碌的一天有了片刻停顿。你把这点放松记下来，也是在珍惜今天。"
    validate_output(output, diary)


@pytest.mark.parametrize(
    "output",
    [
        "你可能患有轻度抑郁，建议立刻治疗并按医生要求服药，这样你的生活一定很快就会彻底恢复正常。",
        "你一定会成功，加油，你可以的。未来所有困难都会过去，今天的你值得全世界最热烈的掌声和肯定。",
    ],
)
def test_guardrail_blocks_diagnosis_and_generic_claims(output: str) -> None:
    with pytest.raises(OutputGuardrailError):
        validate_output(output, "今天工作很累，但还是完成了任务。")
