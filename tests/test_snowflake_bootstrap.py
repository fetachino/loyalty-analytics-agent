from pathlib import Path


def test_bootstrap_grants_sync_permissions_to_existing_and_future_tables() -> None:
    script = Path("infra/snowflake/bootstrap.sql").read_text(encoding="utf-8")

    assert (
        "GRANT SELECT, INSERT, DELETE ON ALL TABLES IN SCHEMA LOYALTY_ANALYTICS.ANALYTICS" in script
    )
    assert (
        "GRANT SELECT, INSERT, DELETE ON FUTURE TABLES IN SCHEMA "
        "LOYALTY_ANALYTICS.ANALYTICS" in script
    )
