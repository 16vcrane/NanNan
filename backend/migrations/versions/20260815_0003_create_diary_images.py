"""create diary images

Revision ID: 20260815_0003
Revises: 20260815_0002
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_0003"
down_revision = "20260815_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diary_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), server_default=sa.text("'image/jpeg'"), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["diary_id"], ["diary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_diary_images_diary_id", "diary_images", ["diary_id"])
    op.create_index("ix_diary_images_user_status", "diary_images", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_diary_images_user_status", table_name="diary_images")
    op.drop_index("ix_diary_images_diary_id", table_name="diary_images")
    op.drop_table("diary_images")
