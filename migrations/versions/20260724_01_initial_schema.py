"""Create loyalty data tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("loyalty_tier", sa.String(20), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False),
        sa.Column("join_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("points_balance >= 0", name="ck_customers_points_balance_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("merchant", sa.String(150), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("purchase_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("points_earned", sa.Integer(), nullable=False),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points_earned >= 0", name="ck_transactions_points_nonnegative"),
        sa.CheckConstraint("purchase_amount >= 0", name="ck_transactions_amount_nonnegative"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])
    op.create_index("ix_transactions_purchase_date", "transactions", ["purchase_date"])
    op.create_table(
        "rewards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("reward_name", sa.String(150), nullable=False),
        sa.Column("points_used", sa.Integer(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points_used > 0", name="ck_rewards_points_positive"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rewards_customer_id", "rewards", ["customer_id"])
    op.create_index("ix_rewards_redeemed_at", "rewards", ["redeemed_at"])


def downgrade() -> None:
    op.drop_table("rewards")
    op.drop_table("transactions")
    op.drop_table("customers")
