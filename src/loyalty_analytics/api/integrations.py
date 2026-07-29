import logging
import secrets

import snowflake.connector
from fastapi import APIRouter, Header, HTTPException, status

from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.config import Settings, get_settings
from loyalty_analytics.schemas import SnowflakeSyncResponse
from loyalty_analytics.services.snowflake_sync import sync_snowflake

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])
logger = logging.getLogger(__name__)


def _redact_snowflake_error(exc: Exception, settings: Settings) -> str:
    message = str(exc)
    secrets_to_redact = (
        settings.snowflake_sync_token,
        settings.snowflake_password,
        settings.snowflake_private_key_passphrase,
    )
    for configured_secret in secrets_to_redact:
        if configured_secret is not None:
            secret_value = configured_secret.get_secret_value()
            if secret_value:
                message = message.replace(secret_value, "[REDACTED]")
    return message


def _log_sync_failure(exc: Exception, settings: Settings) -> None:
    logger.error(
        "snowflake_sync_failed",
        extra={
            "error_type": type(exc).__name__,
            "error_code": getattr(exc, "errno", None),
            "sql_state": getattr(exc, "sqlstate", None),
            "error_message": _redact_snowflake_error(exc, settings),
        },
    )


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
        _log_sync_failure(exc, settings)
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
