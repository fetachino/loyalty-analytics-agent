import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import boto3

from loyalty_analytics.config import Settings
from loyalty_analytics.services.analytics_backend import AnalyticsBackend


class ObjectStorageService:
    """Store aggregate analytics snapshots through the S3 API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.object_storage_is_configured:
            raise ValueError("Object storage is not configured")
        self._settings = settings
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint_url,
            region_name=settings.object_storage_region,
            aws_access_key_id=settings.object_storage_access_key_id.get_secret_value()
            if settings.object_storage_access_key_id
            else None,
            aws_secret_access_key=settings.object_storage_secret_access_key.get_secret_value()
            if settings.object_storage_secret_access_key
            else None,
        )

    def upload_analytics_snapshot(
        self,
        backend: AnalyticsBackend,
    ) -> tuple[str, int, str]:
        generated_at = datetime.now(UTC)
        payload = {
            "schema_version": 1,
            "generated_at": generated_at.isoformat(),
            "overview": backend.overview().model_dump(mode="json"),
            "loyalty_tiers": [item.model_dump(mode="json") for item in backend.loyalty_tiers()],
            "spending_categories": [
                item.model_dump(mode="json") for item in backend.spending_categories()
            ],
            "reward_redemptions": [
                item.model_dump(mode="json") for item in backend.reward_redemptions()
            ],
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        checksum = hashlib.sha256(body).hexdigest()
        object_key = generated_at.strftime("analytics/%Y/%m/%d/%H%M%S-%f.json")
        self._client.put_object(
            Bucket=self._settings.object_storage_bucket,
            Key=object_key,
            Body=body,
            ContentType="application/json",
            Metadata={"sha256": checksum, "schema-version": "1"},
        )
        return object_key, len(body), checksum

    def presigned_download_url(self, object_key: str) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.object_storage_bucket,
                    "Key": object_key,
                },
                ExpiresIn=self._settings.object_storage_presigned_expire_seconds,
            )
        )
