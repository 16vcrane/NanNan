"""create structured memory extraction and retrieval audit tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260819_0006"
down_revision = "20260815_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "memory_extractions",
        sa.Column("id", uuid, nullable=False), sa.Column("diary_entry_id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False), sa.Column("status", sa.String(16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("extractor_version", sa.String(32), nullable=False), sa.Column("source_content_hash", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128)), sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Integer()), sa.Column("token_usage", sa.Integer()), sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diary_entry_id", "extractor_version", name="uq_memory_extractions_diary_version"),
    )
    op.create_index("ix_memory_extractions_user_status", "memory_extractions", ["user_id", "status"])
    op.create_table(
        "memory_items",
        sa.Column("id", uuid, nullable=False), sa.Column("extraction_id", uuid, nullable=False),
        sa.Column("diary_entry_id", uuid, nullable=False), sa.Column("user_id", uuid, nullable=False),
        sa.Column("type", sa.String(24), nullable=False), sa.Column("label", sa.String(96), nullable=False),
        sa.Column("normalized_value", sa.String(96), nullable=False), sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_start", sa.Integer(), nullable=False), sa.Column("evidence_end", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False), sa.Column("occurred_on", sa.Date()),
        sa.Column("attributes_json", sa.JSON(), nullable=False), sa.Column("review_status", sa.String(16), server_default=sa.text("'auto'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["extraction_id"], ["memory_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_items_user_type_date", "memory_items", ["user_id", "type", "occurred_on"])
    op.create_index("ix_memory_items_user_normalized", "memory_items", ["user_id", "normalized_value"])
    op.create_index("ix_memory_items_diary", "memory_items", ["diary_entry_id"])
    op.create_table(
        "retrieval_runs",
        sa.Column("id", uuid, nullable=False), sa.Column("request_id", sa.String(128)), sa.Column("user_id", uuid, nullable=False),
        sa.Column("diary_entry_id", uuid, nullable=False), sa.Column("retriever_version", sa.String(32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False), sa.Column("selected_memory_ids", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False), sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_retrieval_runs_user_diary", "retrieval_runs", ["user_id", "diary_entry_id"])


def downgrade() -> None:
    op.drop_index("ix_retrieval_runs_user_diary", table_name="retrieval_runs")
    op.drop_table("retrieval_runs")
    op.drop_index("ix_memory_items_diary", table_name="memory_items")
    op.drop_index("ix_memory_items_user_normalized", table_name="memory_items")
    op.drop_index("ix_memory_items_user_type_date", table_name="memory_items")
    op.drop_table("memory_items")
    op.drop_index("ix_memory_extractions_user_status", table_name="memory_extractions")
    op.drop_table("memory_extractions")
