"""Add per-user AI query history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_03"
down_revision: str | None = "20260724_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_query_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("response_id", sa.String(200), nullable=False),
        sa.Column("tools_used", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_query_history_user_created",
        "agent_query_history",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("agent_query_history")
