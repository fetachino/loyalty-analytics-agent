from loyalty_analytics.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Loyalty Analytics API"
    assert settings.app_env == "development"
    assert settings.agent_rate_limit_requests == 10
    assert settings.agent_rate_limit_window_seconds == 60
