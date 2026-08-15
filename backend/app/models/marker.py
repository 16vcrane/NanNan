import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TimelineMarker(Base):
    __tablename__ = "timeline_markers"
    __table_args__ = (
        CheckConstraint(
            "type IN ('growth', 'relationship', 'place', 'achievement', 'custom')",
            name="ck_timeline_markers_type",
        ),
        CheckConstraint(
            "sort_order BETWEEN 0 AND 2",
            name="ck_timeline_markers_sort_order",
        ),
        Index("ix_timeline_markers_diary_entry_id", "diary_entry_id"),
        Index("ix_timeline_markers_user_diary", "user_id", "diary_entry_id"),
        UniqueConstraint(
            "diary_entry_id",
            "keyword",
            name="uq_timeline_markers_diary_keyword",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diary_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diary_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    keyword: Mapped[str] = mapped_column(String(32), nullable=False)
    display_text: Mapped[str] = mapped_column(String(48), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
