"""Add agent workflow approval audit records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_04"
down_revision: str | None = "20260724_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_workflow_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id"),
    )
    op.create_index(
        "ix_agent_workflow_audit_user_created",
        "agent_workflow_audit",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("agent_workflow_audit")
