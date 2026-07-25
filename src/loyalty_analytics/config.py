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
    agent_rate_limit_requests: int = Field(default=10, ge=1)
    agent_rate_limit_window_seconds: int = Field(default=60, ge=1)
    auth_secret_key: SecretStr | None = Field(default=None, repr=False)
    auth_token_expire_minutes: int = Field(default=480, ge=5, le=10_080)
    auth_cookie_secure: bool = False
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5.6-sol"
    database_url: str = Field(
        default="postgresql+psycopg://loyalty:loyalty@localhost:5432/loyalty",
        repr=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
