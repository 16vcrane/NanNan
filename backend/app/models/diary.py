import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        CheckConstraint(
            "char_length(content) <= 3000 AND char_length(btrim(content)) > 0",
            name="ck_diary_entries_content_length",
        ),
        CheckConstraint(
            "energy_score BETWEEN 0 AND 100",
            name="ck_diary_entries_energy_score",
        ),
        Index("ix_diary_entries_user_created_at", "user_id", "created_at"),
        Index("ix_diary_entries_user_deleted_at", "user_id", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    energy_score: Mapped[int] = mapped_column(
        Integer, server_default=text("50"), nullable=False
    )
    mood_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    privacy_status: Mapped[str] = mapped_column(
        String(16), server_default=text("'private'"), nullable=False
    )
    ai_reflection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
