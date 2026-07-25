import csv
import io

from fastapi.testclient import TestClient


def _rows(response_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(response_text)))


def test_export_customers(client: TestClient) -> None:
    response = client.get("/api/v1/exports/customers.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "loyalty-customers.csv" in response.headers["content-disposition"]
    rows = _rows(response.text)
    assert len(rows) == 1
    assert rows[0]["email"] == "maya@example.com"


def test_export_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/exports/transactions.csv")
    rows = _rows(response.text)
    assert response.status_code == 200
    assert rows[0]["purchase_amount"] == "24.50"
    assert rows[0]["category"] == "Dining"


def test_export_rewards(client: TestClient) -> None:
    response = client.get("/api/v1/exports/rewards.csv")
    rows = _rows(response.text)
    assert response.status_code == 200
    assert rows[0]["reward_name"] == "$5 Account Credit"
    assert rows[0]["points_used"] == "500"


def test_export_summary(client: TestClient) -> None:
    response = client.get("/api/v1/exports/summary.csv")
    rows = _rows(response.text)
    metrics = {row["metric"]: row["value"] for row in rows}
    assert response.status_code == 200
    assert metrics["total_customers"] == "1"
    assert metrics["total_purchase_amount"] == "24.50"
