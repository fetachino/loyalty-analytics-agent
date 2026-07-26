import logging
from collections.abc import Callable
from contextlib import closing
from decimal import Decimal
from typing import Any, Protocol, TypeVar

import snowflake.connector
from sqlalchemy.orm import Session

from loyalty_analytics.config import Settings, get_settings
from loyalty_analytics.schemas import (
    AnalyticsOverview,
    CategoryAnalytics,
    LoyaltyTierAnalytics,
    RewardAnalytics,
)
from loyalty_analytics.services.analytics import (
    get_loyalty_tiers,
    get_overview,
    get_reward_redemptions,
    get_spending_categories,
)

logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")


class AnalyticsBackend(Protocol):
    """Provider-neutral aggregate analytics interface."""

    def overview(self) -> AnalyticsOverview: ...

    def loyalty_tiers(self) -> list[LoyaltyTierAnalytics]: ...

    def spending_categories(self) -> list[CategoryAnalytics]: ...

    def reward_redemptions(self) -> list[RewardAnalytics]: ...


class PostgreSQLAnalyticsBackend:
    def __init__(self, db: Session) -> None:
        self._db = db

    def overview(self) -> AnalyticsOverview:
        return get_overview(self._db)

    def loyalty_tiers(self) -> list[LoyaltyTierAnalytics]:
        return get_loyalty_tiers(self._db)

    def spending_categories(self) -> list[CategoryAnalytics]:
        return get_spending_categories(self._db)

    def reward_redemptions(self) -> list[RewardAnalytics]:
        return get_reward_redemptions(self._db)


class SnowflakeAnalyticsBackend:
    """Read aggregate loyalty metrics from a least-privilege Snowflake role."""

    def __init__(self, settings: Settings) -> None:
        if not settings.snowflake_is_configured:
            raise ValueError("Snowflake analytics provider is not fully configured")
        self._settings = settings

    def connect(self) -> Any:
        settings = self._settings
        connection_options: dict[str, Any] = {
            "account": settings.snowflake_account,
            "user": settings.snowflake_user,
            "warehouse": settings.snowflake_warehouse,
            "database": settings.snowflake_database,
            "schema": settings.snowflake_schema,
            "role": settings.snowflake_role,
            "application": "loyalty_analytics_agent",
            "login_timeout": 10,
            "network_timeout": 30,
            "session_parameters": {"QUERY_TAG": "loyalty-analytics-agent"},
        }
        if settings.snowflake_password:
            connection_options["password"] = settings.snowflake_password.get_secret_value()
        return snowflake.connector.connect(**connection_options)

    def _fetchall(self, query: str) -> list[tuple[Any, ...]]:
        with closing(self.connect()) as connection, closing(connection.cursor()) as cursor:
            cursor.execute(query)
            return list(cursor.fetchall())

    def overview(self) -> AnalyticsOverview:
        row = self._fetchall(
            """
            SELECT
              (SELECT COUNT(*) FROM CUSTOMERS),
              (SELECT COALESCE(SUM(POINTS_BALANCE), 0) FROM CUSTOMERS),
              (SELECT COUNT(*) FROM TRANSACTIONS),
              (SELECT COUNT(DISTINCT CUSTOMER_ID) FROM TRANSACTIONS),
              (SELECT COALESCE(SUM(PURCHASE_AMOUNT), 0) FROM TRANSACTIONS),
              (SELECT COALESCE(AVG(PURCHASE_AMOUNT), 0) FROM TRANSACTIONS),
              (SELECT COALESCE(SUM(POINTS_EARNED), 0) FROM TRANSACTIONS),
              (SELECT COUNT(*) FROM REWARDS),
              (SELECT COALESCE(SUM(POINTS_USED), 0) FROM REWARDS)
            """
        )[0]
        return AnalyticsOverview(
            total_customers=row[0],
            total_points_balance=row[1],
            total_transactions=row[2],
            active_customers=row[3],
            total_purchase_amount=Decimal(str(row[4])),
            average_purchase_amount=Decimal(str(row[5])),
            total_points_earned=row[6],
            total_rewards_redeemed=row[7],
            total_points_redeemed=row[8],
        )

    def loyalty_tiers(self) -> list[LoyaltyTierAnalytics]:
        rows = self._fetchall(
            """
            SELECT LOYALTY_TIER, COUNT(*), COALESCE(SUM(POINTS_BALANCE), 0),
                   COALESCE(AVG(POINTS_BALANCE), 0)
            FROM CUSTOMERS GROUP BY LOYALTY_TIER ORDER BY LOYALTY_TIER
            """
        )
        return [
            LoyaltyTierAnalytics(
                loyalty_tier=row[0],
                customer_count=row[1],
                total_points_balance=row[2],
                average_points_balance=Decimal(str(row[3])),
            )
            for row in rows
        ]

    def spending_categories(self) -> list[CategoryAnalytics]:
        rows = self._fetchall(
            """
            SELECT CATEGORY, COUNT(*), SUM(PURCHASE_AMOUNT), AVG(PURCHASE_AMOUNT),
                   SUM(POINTS_EARNED)
            FROM TRANSACTIONS GROUP BY CATEGORY
            ORDER BY SUM(PURCHASE_AMOUNT) DESC, CATEGORY
            """
        )
        return [
            CategoryAnalytics(
                category=row[0],
                transaction_count=row[1],
                total_purchase_amount=Decimal(str(row[2])),
                average_purchase_amount=Decimal(str(row[3])),
                total_points_earned=row[4],
            )
            for row in rows
        ]

    def reward_redemptions(self) -> list[RewardAnalytics]:
        rows = self._fetchall(
            """
            SELECT REWARD_NAME, COUNT(*), SUM(POINTS_USED), AVG(POINTS_USED)
            FROM REWARDS GROUP BY REWARD_NAME ORDER BY COUNT(*) DESC, REWARD_NAME
            """
        )
        return [
            RewardAnalytics(
                reward_name=row[0],
                redemption_count=row[1],
                total_points_used=row[2],
                average_points_used=Decimal(str(row[3])),
            )
            for row in rows
        ]

    def ping(self) -> None:
        self._fetchall("SELECT 1")


class FallbackAnalyticsBackend:
    def __init__(self, primary: AnalyticsBackend, fallback: AnalyticsBackend) -> None:
        self._primary = primary
        self._fallback = fallback

    def _run(self, operation: Callable[[AnalyticsBackend], ResultT]) -> ResultT:
        try:
            return operation(self._primary)
        except snowflake.connector.Error:
            logger.exception("Snowflake query failed; using PostgreSQL analytics fallback")
            return operation(self._fallback)

    def overview(self) -> AnalyticsOverview:
        return self._run(lambda backend: backend.overview())

    def loyalty_tiers(self) -> list[LoyaltyTierAnalytics]:
        return self._run(lambda backend: backend.loyalty_tiers())

    def spending_categories(self) -> list[CategoryAnalytics]:
        return self._run(lambda backend: backend.spending_categories())

    def reward_redemptions(self) -> list[RewardAnalytics]:
        return self._run(lambda backend: backend.reward_redemptions())


def get_analytics_backend(db: Session, settings: Settings | None = None) -> AnalyticsBackend:
    """Build the configured analytics provider for one request or agent turn."""
    resolved_settings = settings or get_settings()
    postgresql = PostgreSQLAnalyticsBackend(db)
    if resolved_settings.analytics_provider != "snowflake":
        return postgresql
    if not resolved_settings.snowflake_is_configured:
        if resolved_settings.snowflake_fallback_to_postgresql:
            logger.warning("Snowflake is selected but not configured; using PostgreSQL fallback")
            return postgresql
        raise ValueError("Snowflake analytics provider is not fully configured")
    snowflake = SnowflakeAnalyticsBackend(resolved_settings)
    if resolved_settings.snowflake_fallback_to_postgresql:
        return FallbackAnalyticsBackend(snowflake, postgresql)
    return snowflake
