"""Synchronize PostgreSQL loyalty data to Snowflake."""

from collections.abc import Iterable, Sequence
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import snowflake.connector
from sqlalchemy import select
from sqlalchemy.orm import Session

from loyalty_analytics.config import Settings
from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.services.analytics_backend import SnowflakeAnalyticsBackend


@dataclass(frozen=True)
class SnowflakeSyncResult:
    customers: int
    transactions: int
    rewards: int


def _insert_rows(
    cursor: Any,
    table: str,
    columns: Sequence[str],
    rows: Iterable[tuple[Any, ...]],
) -> int:
    materialized = list(rows)
    placeholders = ", ".join(["%s"] * len(columns))
    cursor.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        materialized,
    )
    return len(materialized)


def sync_snowflake(db: Session, settings: Settings) -> SnowflakeSyncResult:
    """Atomically replace Snowflake analytics tables with PostgreSQL source data."""
    backend = SnowflakeAnalyticsBackend(settings)
    customers = list(db.scalars(select(Customer).order_by(Customer.id)))
    transactions = list(db.scalars(select(Transaction).order_by(Transaction.id)))
    rewards = list(db.scalars(select(Reward).order_by(Reward.id)))

    with closing(backend.connect()) as connection, closing(connection.cursor()) as cursor:
        try:
            for table in ("REWARDS", "TRANSACTIONS", "CUSTOMERS"):
                cursor.execute(f"DELETE FROM {table}")
            customer_count = _insert_rows(
                cursor,
                "CUSTOMERS",
                (
                    "ID",
                    "FIRST_NAME",
                    "LAST_NAME",
                    "EMAIL",
                    "CITY",
                    "STATE",
                    "LOYALTY_TIER",
                    "POINTS_BALANCE",
                    "JOIN_DATE",
                    "CREATED_AT",
                    "UPDATED_AT",
                ),
                (
                    (
                        str(item.id),
                        item.first_name,
                        item.last_name,
                        item.email,
                        item.city,
                        item.state,
                        item.loyalty_tier,
                        item.points_balance,
                        item.join_date,
                        item.created_at,
                        item.updated_at,
                    )
                    for item in customers
                ),
            )
            transaction_count = _insert_rows(
                cursor,
                "TRANSACTIONS",
                (
                    "ID",
                    "CUSTOMER_ID",
                    "MERCHANT",
                    "CATEGORY",
                    "PURCHASE_AMOUNT",
                    "POINTS_EARNED",
                    "PURCHASE_DATE",
                ),
                (
                    (
                        str(item.id),
                        str(item.customer_id),
                        item.merchant,
                        item.category,
                        item.purchase_amount,
                        item.points_earned,
                        item.purchase_date,
                    )
                    for item in transactions
                ),
            )
            reward_count = _insert_rows(
                cursor,
                "REWARDS",
                ("ID", "CUSTOMER_ID", "REWARD_NAME", "POINTS_USED", "REDEEMED_AT"),
                (
                    (
                        str(item.id),
                        str(item.customer_id),
                        item.reward_name,
                        item.points_used,
                        item.redeemed_at,
                    )
                    for item in rewards
                ),
            )
            connection.commit()
        except snowflake.connector.Error:
            connection.rollback()
            raise
    return SnowflakeSyncResult(
        customers=customer_count,
        transactions=transaction_count,
        rewards=reward_count,
    )
