from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Loyalty Analytics API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5.6-sol"
    database_url: str = Field(
        default="postgresql+psycopg://loyalty:loyalty@localhost:5432/loyalty",
        repr=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
