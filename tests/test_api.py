import uuid

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_customers_returns_page(client: TestClient) -> None:
    response = client.get("/api/v1/customers?page=1&page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["pages"] == 1
    assert body["items"][0]["email"] == "maya@example.com"


def test_get_customer(client: TestClient) -> None:
    customer = client.get("/api/v1/customers").json()["items"][0]
    response = client.get(f"/api/v1/customers/{customer['id']}")
    assert response.status_code == 200
    assert response.json()["first_name"] == "Maya"


def test_missing_customer_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_invalid_customer_id_returns_422(client: TestClient) -> None:
    assert client.get("/api/v1/customers/not-a-uuid").status_code == 422


def test_list_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert response.json()["items"][0]["purchase_amount"] == "24.50"


def test_list_rewards(client: TestClient) -> None:
    response = client.get("/api/v1/rewards")
    assert response.status_code == 200
    assert response.json()["items"][0]["points_used"] == 500


def test_pagination_validation(client: TestClient) -> None:
    assert client.get("/api/v1/customers?page=0").status_code == 422
    assert client.get("/api/v1/customers?page_size=101").status_code == 422


def test_empty_page_preserves_total(client: TestClient) -> None:
    body = client.get("/api/v1/customers?page=2&page_size=1").json()
    assert body["items"] == []
    assert body["total"] == 1
    assert body["pages"] == 1
