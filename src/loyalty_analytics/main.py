import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from loyalty_analytics.api.agent import router as agent_router
from loyalty_analytics.api.auth import router as auth_router
from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.api.router import router
from loyalty_analytics.config import get_settings
from loyalty_analytics.observability import RequestContextMiddleware, configure_logging
from loyalty_analytics.schemas import HealthResponse, ReadinessResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logging.getLogger(__name__).info("application_started")
    yield


settings = get_settings()
static_directory = Path(__file__).parent / "static"
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="REST API for customer loyalty, transaction, and reward data.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(agent_router)
app.include_router(auth_router)
app.add_middleware(RequestContextMiddleware)
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False, response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(static_directory / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@app.get("/health/live", response_model=HealthResponse, tags=["Operations"])
def liveness() -> HealthResponse:
    return HealthResponse(status="healthy")


@app.get("/health/ready", response_model=ReadinessResponse, tags=["Operations"])
def readiness(db: DatabaseSession) -> ReadinessResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return ReadinessResponse(status="ready", database="connected")
