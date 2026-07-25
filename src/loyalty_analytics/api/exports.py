import csv
import io
from collections.abc import Iterable, Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from loyalty_analytics.api.auth import get_current_user
from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.services.analytics import get_overview

router = APIRouter(
    prefix="/api/v1/exports",
    tags=["Exports"],
    dependencies=[Depends(get_current_user)],
)


def _safe_cell(value: Any) -> str:
    if isinstance(value, datetime | date):
        text = value.isoformat()
    elif isinstance(value, Decimal):
        text = f"{value:.2f}"
    else:
        text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def _csv_rows(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    yield buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow([_safe_cell(value) for value in row])
        yield buffer.getvalue()


def _download(filename: str, rows: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(
        rows,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/customers.csv", response_class=StreamingResponse)
def export_customers(db: DatabaseSession) -> StreamingResponse:
    customers = db.scalars(select(Customer).order_by(Customer.id)).yield_per(500)
    rows = (
        (
            customer.id,
            customer.first_name,
            customer.last_name,
            customer.email,
            customer.city,
            customer.state,
            customer.loyalty_tier,
            customer.points_balance,
            customer.join_date,
            customer.created_at,
        )
        for customer in customers
    )
    return _download(
        "loyalty-customers.csv",
        _csv_rows(
            (
                "id",
                "first_name",
                "last_name",
                "email",
                "city",
                "state",
                "loyalty_tier",
                "points_balance",
                "join_date",
                "created_at",
            ),
            rows,
        ),
    )


@router.get("/transactions.csv", response_class=StreamingResponse)
def export_transactions(db: DatabaseSession) -> StreamingResponse:
    transactions = db.scalars(select(Transaction).order_by(Transaction.purchase_date)).yield_per(
        500
    )
    rows = (
        (
            transaction.id,
            transaction.customer_id,
            transaction.merchant,
            transaction.category,
            transaction.purchase_amount,
            transaction.points_earned,
            transaction.purchase_date,
        )
        for transaction in transactions
    )
    return _download(
        "loyalty-transactions.csv",
        _csv_rows(
            (
                "id",
                "customer_id",
                "merchant",
                "category",
                "purchase_amount",
                "points_earned",
                "purchase_date",
            ),
            rows,
        ),
    )


@router.get("/rewards.csv", response_class=StreamingResponse)
def export_rewards(db: DatabaseSession) -> StreamingResponse:
    rewards = db.scalars(select(Reward).order_by(Reward.redeemed_at)).yield_per(500)
    rows = (
        (
            reward.id,
            reward.customer_id,
            reward.reward_name,
            reward.points_used,
            reward.redeemed_at,
        )
        for reward in rewards
    )
    return _download(
        "loyalty-rewards.csv",
        _csv_rows(("id", "customer_id", "reward_name", "points_used", "redeemed_at"), rows),
    )


@router.get("/summary.csv", response_class=StreamingResponse)
def export_summary(db: DatabaseSession) -> StreamingResponse:
    overview = get_overview(db)
    rows = ((name, value) for name, value in overview.model_dump().items())
    return _download(
        "loyalty-program-summary.csv",
        _csv_rows(("metric", "value"), rows),
    )
