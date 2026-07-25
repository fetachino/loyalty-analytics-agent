import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from loyalty_analytics.api.agent import router as agent_router
from loyalty_analytics.api.router import router
from loyalty_analytics.config import get_settings
from loyalty_analytics.schemas import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s")
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="REST API for customer loyalty, transaction, and reward data.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(agent_router)


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health() -> HealthResponse:
    return HealthResponse(status="healthy")
