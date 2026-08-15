import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marker import TimelineMarker

MAX_MARKERS_PER_DIARY = 3


@dataclass(frozen=True)
class MarkerRule:
    type: str
    keyword: str
    display_text: str
    color: str


MARKER_RULES: tuple[MarkerRule, ...] = (
    MarkerRule("growth", "学会", "学会", "#789184"),
    MarkerRule("growth", "掌握", "掌握", "#789184"),
    MarkerRule("growth", "第一次", "第一次", "#789184"),
    MarkerRule("growth", "完成", "完成", "#789184"),
    MarkerRule("growth", "通过", "通过", "#789184"),
    MarkerRule("relationship", "认识", "认识", "#B66D61"),
    MarkerRule("relationship", "在一起", "在一起", "#B66D61"),
    MarkerRule("relationship", "分开", "分开", "#B66D61"),
    MarkerRule("relationship", "重逢", "重逢", "#B66D61"),
    MarkerRule("relationship", "纪念日", "纪念日", "#B66D61"),
    MarkerRule("place", "去了", "去了", "#648397"),
    MarkerRule("place", "旅行", "旅行", "#648397"),
    MarkerRule("place", "搬家", "搬家", "#648397"),
    MarkerRule("place", "回到", "回到", "#648397"),
    MarkerRule("place", "离开", "离开", "#648397"),
    MarkerRule("achievement", "拿到", "拿到", "#A56F36"),
    MarkerRule("achievement", "获奖", "获奖", "#A56F36"),
    MarkerRule("achievement", "录取", "录取", "#A56F36"),
    MarkerRule("achievement", "入职", "入职", "#A56F36"),
    MarkerRule("achievement", "毕业", "毕业", "#A56F36"),
)


def extract_markers(content: str) -> list[MarkerRule]:
    matches: list[tuple[int, int, MarkerRule]] = []
    for rule_index, rule in enumerate(MARKER_RULES):
        position = content.find(rule.keyword)
        if position >= 0:
            matches.append((position, rule_index, rule))
    matches.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in matches[:MAX_MARKERS_PER_DIARY]]


def build_marker_models(
    diary_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> list[TimelineMarker]:
    return [
        TimelineMarker(
            diary_entry_id=diary_id,
            user_id=user_id,
            type=rule.type,
            keyword=rule.keyword,
            display_text=rule.display_text,
            color=rule.color,
            sort_order=sort_order,
        )
        for sort_order, rule in enumerate(extract_markers(content))
    ]


async def list_markers_for_diaries(
    db: AsyncSession,
    user_id: uuid.UUID,
    diary_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[TimelineMarker]]:
    grouped = {diary_id: [] for diary_id in diary_ids}
    if not diary_ids:
        return grouped
    result = await db.execute(
        select(TimelineMarker)
        .where(
            TimelineMarker.user_id == user_id,
            TimelineMarker.diary_entry_id.in_(diary_ids),
        )
        .order_by(TimelineMarker.diary_entry_id, TimelineMarker.sort_order)
    )
    for marker in result.scalars().all():
        grouped[marker.diary_entry_id].append(marker)
    return grouped
