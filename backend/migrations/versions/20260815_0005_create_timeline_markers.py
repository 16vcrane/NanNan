"""create timeline markers

Revision ID: 20260815_0005
Revises: 20260815_0004
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_0005"
down_revision = "20260815_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_markers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diary_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("keyword", sa.String(length=32), nullable=False),
        sa.Column("display_text", sa.String(length=48), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('growth', 'relationship', 'place', 'achievement', 'custom')",
            name="ck_timeline_markers_type",
        ),
        sa.CheckConstraint(
            "sort_order BETWEEN 0 AND 2",
            name="ck_timeline_markers_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "diary_entry_id", "keyword", name="uq_timeline_markers_diary_keyword"
        ),
    )
    op.create_index(
        "ix_timeline_markers_diary_entry_id",
        "timeline_markers",
        ["diary_entry_id"],
    )
    op.create_index(
        "ix_timeline_markers_user_diary",
        "timeline_markers",
        ["user_id", "diary_entry_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_markers_user_diary", table_name="timeline_markers")
    op.drop_index(
        "ix_timeline_markers_diary_entry_id", table_name="timeline_markers"
    )
    op.drop_table("timeline_markers")
