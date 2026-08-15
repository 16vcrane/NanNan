"""create ai reflections

Revision ID: 20260815_0004
Revises: 20260815_0003
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_0004"
down_revision = "20260815_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_reflections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diary_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("safety_status", sa.String(length=16), server_default=sa.text("'safe'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diary_entry_id"),
    )
    op.create_index("ix_ai_reflections_diary_entry_id", "ai_reflections", ["diary_entry_id"])
    op.create_index("ix_ai_reflections_user_status", "ai_reflections", ["user_id", "status"])
    op.create_foreign_key(
        "fk_diary_entries_ai_reflection_id",
        "diary_entries",
        "ai_reflections",
        ["ai_reflection_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_diary_entries_ai_reflection_id", "diary_entries", type_="foreignkey")
    op.drop_index("ix_ai_reflections_user_status", table_name="ai_reflections")
    op.drop_index("ix_ai_reflections_diary_entry_id", table_name="ai_reflections")
    op.drop_table("ai_reflections")
