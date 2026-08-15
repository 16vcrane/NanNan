import re
from dataclasses import dataclass


FAILURE_FALLBACK = (
    "今天的这一页已经被好好保存。AI 暂时没有写出回信，"
    "但这些文字会在未来某天重新陪你见到此刻的自己。"
)
SAFETY_FALLBACK = (
    "我能感觉到你现在很难熬。请先不要独自承受这些内容，尽快联系身边可信任的人，"
    "或拨打当地紧急求助电话。你的安全比这篇记录更重要。"
)

CRISIS_PATTERNS = (
    "自杀", "自残", "不想活", "结束生命", "杀死自己", "伤害自己", "轻生",
)
DIAGNOSIS_PATTERNS = (
    r"你(可能|应该|一定)?(患有|得了|有)(轻度|中度|重度)?(抑郁|焦虑|躁郁|精神病)",
    r"建议.{0,8}(治疗|服药|停药|就医)",
)
DANGEROUS_PATTERNS = ("自杀方法", "自残方法", "杀人方法", "具体步骤")


@dataclass(frozen=True)
class InputSafetyResult:
    safe: bool
    safety_status: str


class OutputGuardrailError(ValueError):
    pass


def check_input(content: str) -> InputSafetyResult:
    if any(pattern in content for pattern in CRISIS_PATTERNS):
        return InputSafetyResult(safe=False, safety_status="sensitive")
    return InputSafetyResult(safe=True, safety_status="safe")


def validate_output(content: str, diary_content: str) -> None:
    if not 30 <= len(content) <= 80:
        raise OutputGuardrailError("reflection length is outside 30-80 characters")
    if any(pattern in content for pattern in DANGEROUS_PATTERNS):
        raise OutputGuardrailError("dangerous content detected")
    if any(re.search(pattern, content) for pattern in DIAGNOSIS_PATTERNS):
        raise OutputGuardrailError("diagnosis or treatment language detected")
    if "你一定会成功" in content or "加油，你可以的" in content:
        raise OutputGuardrailError("generic encouragement detected")

    diary_terms = {
        diary_content[index:index + 2]
        for index in range(max(0, len(diary_content) - 1))
        if diary_content[index:index + 2].strip()
    }
    if diary_terms and not any(term in content for term in diary_terms):
        raise OutputGuardrailError("reflection lacks a concrete diary reference")
