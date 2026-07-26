from decimal import Decimal
from unittest.mock import MagicMock

import snowflake.connector
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from loyalty_analytics.config import Settings
from loyalty_analytics.services.analytics_backend import (
    FallbackAnalyticsBackend,
    PostgreSQLAnalyticsBackend,
    SnowflakeAnalyticsBackend,
    get_analytics_backend,
)


def snowflake_settings() -> Settings:
    return Settings(
        _env_file=None,
        analytics_provider="snowflake",
        snowflake_account="organization-account",
        snowflake_user="portfolio_app",
        snowflake_password="not-a-real-secret",
    )


def test_snowflake_overview_maps_query_result(monkeypatch: MonkeyPatch) -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (100, 10_000, 1_000, 100, Decimal("250000.00"), Decimal("250.00"), 250_000, 100, 50_000)
    ]
    connection = MagicMock()
    connection.cursor.return_value = cursor
    monkeypatch.setattr("snowflake.connector.connect", lambda **_: connection)

    result = SnowflakeAnalyticsBackend(snowflake_settings()).overview()

    assert result.total_customers == 100
    assert result.total_transactions == 1_000
    assert result.total_purchase_amount == Decimal("250000.00")
    connection.close.assert_called_once()
    cursor.close.assert_called_once()


def test_fallback_uses_postgresql_after_snowflake_error(db: Session) -> None:
    primary = MagicMock()
    primary.overview.side_effect = snowflake.connector.Error("unavailable")
    backend = FallbackAnalyticsBackend(primary, PostgreSQLAnalyticsBackend(db))

    result = backend.overview()

    assert result.total_customers == 1
    primary.overview.assert_called_once()


def test_provider_defaults_to_postgresql(db: Session) -> None:
    backend = get_analytics_backend(db, Settings(_env_file=None))

    assert isinstance(backend, PostgreSQLAnalyticsBackend)


def test_snowflake_requires_credentials() -> None:
    settings = Settings(_env_file=None, analytics_provider="snowflake")

    assert settings.snowflake_is_configured is False


def test_unconfigured_snowflake_falls_back_to_postgresql(db: Session) -> None:
    settings = Settings(_env_file=None, analytics_provider="snowflake")

    backend = get_analytics_backend(db, settings)

    assert isinstance(backend, PostgreSQLAnalyticsBackend)
