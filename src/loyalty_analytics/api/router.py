import math
import uuid
from typing import Any, TypeVar, cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loyalty_analytics.api.dependencies import DatabaseSession, PageNumber, PageSize
from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.schemas import CustomerRead, Page, RewardRead, TransactionRead

router = APIRouter(prefix="/api/v1")
ModelT = TypeVar("ModelT")


def _paginate(db: Session, model: type[ModelT], page: int, page_size: int) -> Page[ModelT]:
    total = db.scalar(select(func.count()).select_from(model)) or 0
    model_with_id = cast(Any, model)
    statement = (
        select(model).order_by(model_with_id.id).offset((page - 1) * page_size).limit(page_size)
    )
    items = list(db.scalars(statement))
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/customers", response_model=Page[CustomerRead])
def list_customers(
    db: DatabaseSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[CustomerRead]:
    return cast(Page[CustomerRead], _paginate(db, Customer, page, page_size))


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: uuid.UUID, db: DatabaseSession) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.get("/transactions", response_model=Page[TransactionRead])
def list_transactions(
    db: DatabaseSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[TransactionRead]:
    return cast(Page[TransactionRead], _paginate(db, Transaction, page, page_size))


@router.get("/rewards", response_model=Page[RewardRead])
def list_rewards(
    db: DatabaseSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[RewardRead]:
    return cast(Page[RewardRead], _paginate(db, Reward, page, page_size))
