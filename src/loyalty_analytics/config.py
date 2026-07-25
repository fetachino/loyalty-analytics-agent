from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Loyalty Analytics API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    agent_rate_limit_requests: int = Field(default=10, ge=1)
    agent_rate_limit_window_seconds: int = Field(default=60, ge=1)
    agent_approval_expire_minutes: int = Field(default=15, ge=1, le=1_440)
    auth_secret_key: SecretStr | None = Field(default=None, repr=False)
    auth_token_expire_minutes: int = Field(default=480, ge=5, le=10_080)
    auth_cookie_secure: bool = False
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5.6-sol"
    evaluation_judge_model: str = "gpt-5.6-sol"
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "loyalty-analytics-agent"
    database_url: str = Field(
        default="postgresql+psycopg://loyalty:loyalty@localhost:5432/loyalty",
        repr=False,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        if self.app_env != "production":
            return self
        secret = self.auth_secret_key.get_secret_value() if self.auth_secret_key else ""
        if len(secret) < 32:
            raise ValueError("AUTH_SECRET_KEY must contain at least 32 characters in production")
        if not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
