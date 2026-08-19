import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diary import DiaryEntry

MAX_ON_THIS_DAY_ITEMS = 3
DAY_OFFSETS = (30, 100, 365)
SUMMARY_MAX_LENGTH = 80


class InvalidTimezoneError(ValueError):
    pass


@dataclass(frozen=True)
class OnThisDayCandidate:
    diary: DiaryEntry
    local_date: date
    source: str
    distance_days: int
    priority: int


def resolve_timezone(name: str) -> ZoneInfo:
    if not name or len(name) > 64:
        raise InvalidTimezoneError(name)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise InvalidTimezoneError(name) from None


def summarize_content(content: str, max_length: int = SUMMARY_MAX_LENGTH) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length]}..."


def local_day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _candidate_score(candidate: OnThisDayCandidate) -> tuple[int, int, int, int]:
    content_len = len(candidate.diary.content.strip())
    has_mood = 1 if candidate.diary.mood_label else 0
    return (
        candidate.priority,
        candidate.distance_days,
        -(content_len + has_mood),
        -int(candidate.diary.created_at.timestamp()),
    )


def _merge_candidate(
    candidates: dict[uuid.UUID, OnThisDayCandidate],
    diary: DiaryEntry,
    local_date: date,
    source: str,
    priority: int,
    today: date,
) -> None:
    distance_days = (today - local_date).days
    next_candidate = OnThisDayCandidate(
        diary=diary,
        local_date=local_date,
        source=source,
        distance_days=distance_days,
        priority=priority,
    )
    current = candidates.get(diary.id)
    if current is None or _candidate_score(next_candidate) < _candidate_score(current):
        candidates[diary.id] = next_candidate


async def find_on_this_day(
    db: AsyncSession,
    user_id: uuid.UUID,
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> tuple[date, list[OnThisDayCandidate]]:
    zone = resolve_timezone(timezone_name)
    current = (now or datetime.now(timezone.utc)).astimezone(zone)
    today = current.date()
    today_start, _ = local_day_bounds(today, zone)
    target_dates = [today - timedelta(days=offset) for offset in DAY_OFFSETS]
    exact_date_clauses = []
    for target_date in target_dates:
        start, end = local_day_bounds(target_date, zone)
        exact_date_clauses.append(
            and_(DiaryEntry.created_at >= start, DiaryEntry.created_at < end)
        )
    local_created_at = func.timezone(timezone_name, DiaryEntry.created_at)

    result = await db.execute(
        select(DiaryEntry)
        .where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.deleted_at.is_(None),
            DiaryEntry.created_at < today_start,
            or_(
                and_(
                    extract("month", local_created_at) == today.month,
                    extract("day", local_created_at) == today.day,
                ),
                *exact_date_clauses,
            ),
        )
        .order_by(DiaryEntry.created_at.desc(), DiaryEntry.id.desc())
    )
    entries = list(result.scalars().all())

    candidates: dict[uuid.UUID, OnThisDayCandidate] = {}
    for diary in entries:
        local_date = diary.created_at.astimezone(zone).date()
        if local_date >= today:
            continue

        if local_date.month == today.month and local_date.day == today.day:
            _merge_candidate(candidates, diary, local_date, "same_date", 0, today)

        days_ago = (today - local_date).days
        if days_ago in DAY_OFFSETS:
            priority = DAY_OFFSETS.index(days_ago) + 1
            _merge_candidate(
                candidates,
                diary,
                local_date,
                f"{days_ago}d",
                priority,
                today,
            )

    selected = sorted(candidates.values(), key=_candidate_score)[:MAX_ON_THIS_DAY_ITEMS]
    return today, selected
