from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from loyalty_analytics.api.auth import SESSION_COOKIE
from loyalty_analytics.auth import hash_password
from loyalty_analytics.config import Settings
from loyalty_analytics.database import get_db
from loyalty_analytics.main import app
from loyalty_analytics.models import User


def test_login_session_and_logout(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, auth_secret_key="test-secret-with-enough-entropy-123456789")
    monkeypatch.setattr("loyalty_analytics.api.auth.get_settings", lambda: settings)
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=hash_password("correct-horse-battery-staple"),
        is_admin=True,
    )
    db.add(user)
    db.commit()

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        assert client.get("/api/v1/customers").status_code == 401
        failed = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "incorrect-password"},
        )
        assert failed.status_code == 401

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "ADMIN@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert login.status_code == 200
        assert login.json()["user"]["full_name"] == "Admin User"
        assert SESSION_COOKIE in login.cookies
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/customers").status_code == 200

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert client.get("/api/v1/customers").status_code == 401
    app.dependency_overrides.clear()


def test_login_requires_auth_configuration(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(_env_file=None, auth_secret_key=None)
    monkeypatch.setattr("loyalty_analytics.api.auth.get_settings", lambda: settings)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "some-password"},
    )
    assert response.status_code == 503
