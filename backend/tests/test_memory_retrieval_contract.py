from datetime import date
from types import SimpleNamespace

from app.services.memory_retrieval_service import (
    MAX_CONTEXT_CHARS,
    _keyword_overlap,
    _time_relevance,
)


def test_retrieval_keyword_overlap_is_user_text_based() -> None:
    item = SimpleNamespace(
        label="数据库作业",
        normalized_value="数据库",
        evidence_text="完成了数据库作业",
    )
    assert _keyword_overlap({"数据库", "作业"}, item) > 0
    assert _keyword_overlap({"旅行"}, item) == 0


def test_retrieval_time_relevance_is_bounded_and_decays() -> None:
    current = date(2026, 8, 19)
    assert _time_relevance(current, current) == 1
    assert 0 < _time_relevance(current, date(2025, 8, 19)) < 1
    assert _time_relevance(current, date(1900, 1, 1)) == 0


def test_context_budget_is_small_and_deterministic() -> None:
    assert MAX_CONTEXT_CHARS == 600
