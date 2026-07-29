import uuid

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from loyalty_analytics.api.auth import CurrentUser
from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.config import get_settings
from loyalty_analytics.models import AnalyticsSnapshot
from loyalty_analytics.schemas import AnalyticsSnapshotDownload, AnalyticsSnapshotRead
from loyalty_analytics.services.analytics_backend import get_analytics_backend
from loyalty_analytics.services.object_storage import ObjectStorageService

router = APIRouter(prefix="/api/v1/object-storage", tags=["Object storage"])


def _require_admin(user: CurrentUser) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator required")


@router.post("/snapshots", response_model=AnalyticsSnapshotRead, status_code=201)
def create_snapshot(user: CurrentUser, db: DatabaseSession) -> AnalyticsSnapshot:
    _require_admin(user)
    settings = get_settings()
    try:
        object_key, size_bytes, checksum = ObjectStorageService(settings).upload_analytics_snapshot(
            get_analytics_backend(db, settings)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is not configured",
        ) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage upload failed",
        ) from exc
    snapshot = AnalyticsSnapshot(
        created_by_id=user.id,
        object_key=object_key,
        size_bytes=size_bytes,
        checksum_sha256=checksum,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/snapshots", response_model=list[AnalyticsSnapshotRead])
def list_snapshots(user: CurrentUser, db: DatabaseSession) -> list[AnalyticsSnapshot]:
    _require_admin(user)
    return list(db.scalars(select(AnalyticsSnapshot).order_by(AnalyticsSnapshot.created_at.desc())))


@router.get("/snapshots/{snapshot_id}/download", response_model=AnalyticsSnapshotDownload)
def download_snapshot(
    snapshot_id: uuid.UUID,
    user: CurrentUser,
    db: DatabaseSession,
) -> AnalyticsSnapshotDownload:
    _require_admin(user)
    snapshot = db.get(AnalyticsSnapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    settings = get_settings()
    try:
        url = ObjectStorageService(settings).presigned_download_url(snapshot.object_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is not configured",
        ) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage download failed",
        ) from exc
    return AnalyticsSnapshotDownload(
        url=url,
        expires_in_seconds=settings.object_storage_presigned_expire_seconds,
    )
