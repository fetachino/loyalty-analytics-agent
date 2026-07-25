import pytest
from pydantic import ValidationError

from loyalty_analytics.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Loyalty Analytics API"
    assert settings.app_env == "development"
    assert settings.agent_rate_limit_requests == 10
    assert settings.agent_rate_limit_window_seconds == 60


def test_render_database_url_uses_psycopg_driver() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@database/loyalty",
    )
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_requires_secure_authentication() -> None:
    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY"):
        Settings(_env_file=None, app_env="production", auth_secret_key=None)

    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_secret_key="a" * 48,
            auth_cookie_secure=False,
        )

    settings = Settings(
        _env_file=None,
        app_env="production",
        auth_secret_key="a" * 48,
        auth_cookie_secure=True,
    )
    assert settings.app_env == "production"
