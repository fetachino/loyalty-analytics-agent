import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
static_directory = Path(__file__).parent / "static"
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="REST API for customer loyalty, transaction, and reward data.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(agent_router)
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False, response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(static_directory / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health() -> HealthResponse:
    return HealthResponse(status="healthy")
