"""add per-user personal memory flag"""

from alembic import op
import sqlalchemy as sa

revision = "20260819_0007"
down_revision = "20260819_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("personal_memory_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "personal_memory_enabled")
