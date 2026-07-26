"""Replace Snowflake demo tables with the current PostgreSQL loyalty data."""

from loyalty_analytics.config import get_settings
from loyalty_analytics.database import SessionLocal
from loyalty_analytics.services.snowflake_sync import sync_snowflake


def sync() -> None:
    with SessionLocal() as db:
        result = sync_snowflake(db, get_settings())
    print(
        f"Synced {result.customers} customers, {result.transactions} transactions, "
        f"and {result.rewards} rewards to Snowflake."
    )


if __name__ == "__main__":
    sync()
