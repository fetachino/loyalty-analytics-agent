from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from loyalty_analytics.database import Base, get_db
from loyalty_analytics.main import app
from loyalty_analytics.models import Customer, Reward, Transaction

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(engine)
    with TestingSession() as session:
        customer = Customer(
            first_name="Maya",
            last_name="Chen",
            email="maya@example.com",
            city="Indianapolis",
            state="IN",
            loyalty_tier="Gold",
            points_balance=2400,
            join_date=date(2024, 1, 15),
        )
        session.add(customer)
        session.flush()
        session.add(
            Transaction(
                customer_id=customer.id,
                merchant="Juniper Cafe",
                category="Dining",
                purchase_amount=Decimal("24.50"),
                points_earned=24,
                purchase_date=datetime(2026, 7, 1, tzinfo=UTC),
            )
        )
        session.add(
            Reward(
                customer_id=customer.id,
                reward_name="$5 Account Credit",
                points_used=500,
                redeemed_at=datetime(2026, 7, 2, tzinfo=UTC),
            )
        )
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
