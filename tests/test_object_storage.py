import json
from unittest.mock import MagicMock

from pytest import MonkeyPatch
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from loyalty_analytics.config import Settings
from loyalty_analytics.services.analytics_backend import PostgreSQLAnalyticsBackend
from loyalty_analytics.services.object_storage import ObjectStorageService


def storage_settings() -> Settings:
    return Settings(
        _env_file=None,
        object_storage_bucket="loyalty-analytics",
        object_storage_endpoint_url="http://minio:9000",
        object_storage_access_key_id="test-access-key",
        object_storage_secret_access_key="test-secret-key",
    )


def test_snapshot_contains_aggregates_without_customer_pii(
    db: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    client = MagicMock()
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: client)

    object_key, size_bytes, checksum = ObjectStorageService(
        storage_settings()
    ).upload_analytics_snapshot(PostgreSQLAnalyticsBackend(db))

    request = client.put_object.call_args.kwargs
    payload = json.loads(request["Body"])
    assert object_key.startswith("analytics/")
    assert size_bytes == len(request["Body"])
    assert len(checksum) == 64
    assert payload["overview"]["total_customers"] == 1
    assert "maya@example.com" not in request["Body"].decode()
    assert request["Bucket"] == "loyalty-analytics"


def test_presigned_download_uses_short_expiration(monkeypatch: MonkeyPatch) -> None:
    client = MagicMock()
    client.generate_presigned_url.return_value = "http://minio/download"
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: client)

    url = ObjectStorageService(storage_settings()).presigned_download_url("analytics/snapshot.json")

    assert url == "http://minio/download"
    assert client.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 900


def test_snapshot_endpoint_requires_storage_configuration(client: TestClient) -> None:
    response = client.post("/api/v1/object-storage/snapshots")

    assert response.status_code == 503
    assert response.json() == {"detail": "Object storage is not configured"}


def test_snapshot_endpoints_create_audit_and_download_url(
    client: TestClient,
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeStorage:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings

        def upload_analytics_snapshot(
            self, backend: PostgreSQLAnalyticsBackend
        ) -> tuple[str, int, str]:
            return "analytics/2026/07/29/snapshot.json", 512, "a" * 64

        def presigned_download_url(self, object_key: str) -> str:
            return f"https://storage.example/{object_key}?signed=true"

    settings = storage_settings()
    monkeypatch.setattr("loyalty_analytics.api.object_storage.get_settings", lambda: settings)
    monkeypatch.setattr("loyalty_analytics.api.object_storage.ObjectStorageService", FakeStorage)

    created = client.post("/api/v1/object-storage/snapshots")
    snapshots = client.get("/api/v1/object-storage/snapshots")
    downloaded = client.get(f"/api/v1/object-storage/snapshots/{created.json()['id']}/download")

    assert created.status_code == 201
    assert snapshots.json()[0]["checksum_sha256"] == "a" * 64
    assert downloaded.status_code == 200
    assert downloaded.json()["expires_in_seconds"] == 900
