import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Float, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MemoryExtraction(Base):
    __tablename__ = "memory_extractions"
    __table_args__ = (
        UniqueConstraint("diary_entry_id", "extractor_version", name="uq_memory_extractions_diary_version"),
        Index("ix_memory_extractions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diary_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MemoryItem(Base):
    __tablename__ = "memory_items"
    __table_args__ = (
        Index("ix_memory_items_user_type_date", "user_id", "type", "occurred_on"),
        Index("ix_memory_items_user_normalized", "user_id", "normalized_value"),
        Index("ix_memory_items_diary", "diary_entry_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memory_extractions.id", ondelete="CASCADE"), nullable=False)
    diary_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str] = mapped_column(String(96), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(96), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_start: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_end: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), server_default=text("'auto'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RetrievalRun(Base):
    __tablename__ = "retrieval_runs"
    __table_args__ = (Index("ix_retrieval_runs_user_diary", "user_id", "diary_entry_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    diary_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False)
    retriever_version: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_memory_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
