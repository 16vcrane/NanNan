"""create diary entries

Revision ID: 20260815_0002
Revises: 20260815_0001
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_0002"
down_revision = "20260815_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diary_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("energy_score", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("mood_label", sa.String(length=32), nullable=True),
        sa.Column(
            "privacy_status",
            sa.String(length=16),
            server_default=sa.text("'private'"),
            nullable=False,
        ),
        sa.Column("ai_reflection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(content) <= 3000 AND char_length(btrim(content)) > 0",
            name="ck_diary_entries_content_length",
        ),
        sa.CheckConstraint(
            "energy_score BETWEEN 0 AND 100",
            name="ck_diary_entries_energy_score",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diary_entries_user_created_at",
        "diary_entries",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_diary_entries_user_deleted_at",
        "diary_entries",
        ["user_id", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_diary_entries_user_deleted_at", table_name="diary_entries")
    op.drop_index("ix_diary_entries_user_created_at", table_name="diary_entries")
    op.drop_table("diary_entries")
