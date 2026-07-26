import secrets

import snowflake.connector
from fastapi import APIRouter, Header, HTTPException, status

from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.config import get_settings
from loyalty_analytics.schemas import SnowflakeSyncResponse
from loyalty_analytics.services.snowflake_sync import sync_snowflake

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


@router.post(
    "/snowflake/sync",
    response_model=SnowflakeSyncResponse,
    summary="Synchronize PostgreSQL analytics data to Snowflake",
)
def synchronize_snowflake(
    db: DatabaseSession,
    authorization: str | None = Header(default=None),
) -> SnowflakeSyncResponse:
    settings = get_settings()
    configured_token = (
        settings.snowflake_sync_token.get_secret_value() if settings.snowflake_sync_token else ""
    )
    supplied_token = ""
    if authorization and authorization.startswith("Bearer "):
        supplied_token = authorization.removeprefix("Bearer ")
    if not configured_token or not secrets.compare_digest(supplied_token, configured_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    try:
        result = sync_snowflake(db, settings)
    except (snowflake.connector.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Snowflake synchronization failed",
        ) from exc
    return SnowflakeSyncResponse(
        status="synchronized",
        customers=result.customers,
        transactions=result.transactions,
        rewards=result.rewards,
    )
