from pytest import MonkeyPatch
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
