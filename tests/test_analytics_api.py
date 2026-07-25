from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from loyalty_analytics.models import Customer, Reward, Transaction


def test_analytics_overview(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    assert response.json() == {
        "total_customers": 1,
        "active_customers": 1,
        "total_transactions": 1,
        "total_purchase_amount": "24.50",
        "average_purchase_amount": "24.50",
        "total_points_balance": 2400,
        "total_points_earned": 24,
        "total_rewards_redeemed": 1,
        "total_points_redeemed": 500,
    }


def test_loyalty_tier_analytics(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/loyalty-tiers")
    assert response.status_code == 200
    assert response.json() == [
        {
            "loyalty_tier": "Gold",
            "customer_count": 1,
            "total_points_balance": 2400,
            "average_points_balance": "2400.00",
        }
    ]


def test_spending_category_analytics(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/spending-by-category")
    assert response.status_code == 200
    assert response.json() == [
        {
            "category": "Dining",
            "transaction_count": 1,
            "total_purchase_amount": "24.50",
            "average_purchase_amount": "24.50",
            "total_points_earned": 24,
        }
    ]


def test_reward_redemption_analytics(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/reward-redemptions")
    assert response.status_code == 200
    assert response.json() == [
        {
            "reward_name": "$5 Account Credit",
            "redemption_count": 1,
            "total_points_used": 500,
            "average_points_used": "500.00",
        }
    ]


def test_empty_analytics(client: TestClient, db: Session) -> None:
    db.execute(delete(Reward))
    db.execute(delete(Transaction))
    db.execute(delete(Customer))
    db.commit()

    overview = client.get("/api/v1/analytics/overview")
    assert overview.status_code == 200
    assert overview.json()["total_customers"] == 0
    assert overview.json()["total_purchase_amount"] == "0.00"
    assert client.get("/api/v1/analytics/loyalty-tiers").json() == []
    assert client.get("/api/v1/analytics/spending-by-category").json() == []
    assert client.get("/api/v1/analytics/reward-redemptions").json() == []
