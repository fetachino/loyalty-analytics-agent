import logging
from typing import Any, cast

import snowflake.connector
from pytest import LogCaptureFixture, MonkeyPatch
from starlette.testclient import TestClient

from loyalty_analytics.config import Settings
from loyalty_analytics.services.snowflake_sync import SnowflakeSyncResult


def test_snowflake_sync_rejects_missing_token(client: TestClient) -> None:
    response = client.post("/api/v1/integrations/snowflake/sync")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_snowflake_sync_returns_counts(
    client: TestClient,
    monkeypatch: MonkeyPatch,
) -> None:
    settings = Settings(_env_file=None, snowflake_sync_token="scheduled-sync-secret")
    monkeypatch.setattr(
        "loyalty_analytics.api.integrations.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "loyalty_analytics.api.integrations.sync_snowflake",
        lambda db, resolved_settings: SnowflakeSyncResult(100, 1_000, 100),
    )

    response = client.post(
        "/api/v1/integrations/snowflake/sync",
        headers={"Authorization": "Bearer scheduled-sync-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "synchronized",
        "customers": 100,
        "transactions": 1_000,
        "rewards": 100,
    }


def test_snowflake_sync_logs_redacted_failure_context(
    client: TestClient,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    password = "never-log-this-password"
    settings = Settings(
        _env_file=None,
        snowflake_sync_token="scheduled-sync-secret",
        snowflake_password=password,
    )
    monkeypatch.setattr(
        "loyalty_analytics.api.integrations.get_settings",
        lambda: settings,
    )

    def fail_sync(*_: object) -> SnowflakeSyncResult:
        raise snowflake.connector.ProgrammingError(
            msg=f"Warehouse unavailable using {password}",
            errno=2003,
            sqlstate="42501",
        )

    monkeypatch.setattr(
        "loyalty_analytics.api.integrations.sync_snowflake",
        fail_sync,
    )

    with caplog.at_level(logging.ERROR, logger="loyalty_analytics.api.integrations"):
        response = client.post(
            "/api/v1/integrations/snowflake/sync",
            headers={"Authorization": "Bearer scheduled-sync-secret"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Snowflake synchronization failed"}
    record = next(record for record in caplog.records if record.message == "snowflake_sync_failed")
    context = cast(Any, record)
    assert context.error_type == "ProgrammingError"
    assert context.error_code == 2003
    assert context.sql_state == "42501"
    assert "Warehouse unavailable using [REDACTED]" in context.error_message
    assert password not in caplog.text
