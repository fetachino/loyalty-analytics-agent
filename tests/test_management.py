import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from loyalty_analytics.api.auth import get_current_user
from loyalty_analytics.main import app
from loyalty_analytics.models import User


def _customer_id(client: TestClient) -> str:
    return str(client.get("/api/v1/customers").json()["items"][0]["id"])


def test_admin_creates_customer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/customers",
        json={
            "first_name": "  Jordan ",
            "last_name": " Rivera ",
            "email": " JORDAN@example.com ",
            "city": " Carmel ",
            "state": "in",
            "loyalty_tier": "Silver",
            "join_date": "2026-07-29",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Jordan"
    assert body["email"] == "jordan@example.com"
    assert body["state"] == "IN"
    assert body["points_balance"] == 0


def test_duplicate_customer_email_returns_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/customers",
        json={
            "first_name": "Another",
            "last_name": "Customer",
            "email": "MAYA@example.com",
            "city": "Indianapolis",
            "state": "IN",
            "loyalty_tier": "Bronze",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "A customer with this email already exists"


def test_admin_updates_customer(client: TestClient) -> None:
    response = client.patch(
        f"/api/v1/admin/customers/{_customer_id(client)}",
        json={"city": " Bloomington ", "state": "in", "loyalty_tier": "Platinum"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Bloomington"
    assert body["state"] == "IN"
    assert body["loyalty_tier"] == "Platinum"


def test_transaction_increases_customer_points(client: TestClient) -> None:
    customer_id = _customer_id(client)
    response = client.post(
        "/api/v1/admin/transactions",
        json={
            "customer_id": customer_id,
            "merchant": "North Market",
            "category": "Grocery",
            "purchase_amount": "42.75",
            "points_earned": 43,
            "purchase_date": datetime(2026, 7, 29, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["purchase_amount"] == "42.75"
    customer = client.get(f"/api/v1/customers/{customer_id}").json()
    assert customer["points_balance"] == 2443


def test_reward_deducts_customer_points(client: TestClient) -> None:
    customer_id = _customer_id(client)
    response = client.post(
        "/api/v1/admin/rewards",
        json={
            "customer_id": customer_id,
            "reward_name": "$10 Account Credit",
            "points_used": 1000,
        },
    )

    assert response.status_code == 201
    customer = client.get(f"/api/v1/customers/{customer_id}").json()
    assert customer["points_balance"] == 1400


def test_reward_rejects_insufficient_points(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/rewards",
        json={
            "customer_id": _customer_id(client),
            "reward_name": "Luxury Trip",
            "points_used": 500_000,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Customer does not have enough points"


def test_management_rejects_missing_customer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/transactions",
        json={
            "customer_id": str(uuid.uuid4()),
            "merchant": "North Market",
            "category": "Grocery",
            "purchase_amount": "10.00",
            "points_earned": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_management_requires_administrator(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid.uuid4(),
        email="viewer@example.com",
        full_name="Read Only Viewer",
        password_hash="unused",
        is_active=True,
        is_admin=False,
    )

    response = client.post(
        "/api/v1/admin/customers",
        json={
            "first_name": "Read",
            "last_name": "Only",
            "email": "readonly@example.com",
            "city": "Indianapolis",
            "state": "IN",
            "loyalty_tier": "Bronze",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required"
