"""Seed demonstration loyalty data only when the customer table is empty."""

from sqlalchemy import func, select

from loyalty_analytics.database import SessionLocal
from loyalty_analytics.models import Customer
from scripts.seed import seed


def main() -> None:
    with SessionLocal() as session:
        customer_count = session.scalar(select(func.count()).select_from(Customer)) or 0
    if customer_count:
        print(f"Demo data already exists ({customer_count} customers); skipping seed.")
        return
    seed()


if __name__ == "__main__":
    main()
