import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from loyalty_analytics.api.auth import AdminUser
from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.schemas import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    RewardCreate,
    RewardRead,
    TransactionCreate,
    TransactionRead,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Data Management"])


def _customer_or_404(db: DatabaseSession, customer_id: uuid.UUID) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def _lock_customer_or_404(db: DatabaseSession, customer_id: uuid.UUID) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id).with_for_update())
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def _email_exists(db: DatabaseSession, email: str, exclude_id: uuid.UUID | None = None) -> bool:
    statement = select(Customer.id).where(Customer.email == email)
    if exclude_id is not None:
        statement = statement.where(Customer.id != exclude_id)
    return db.scalar(statement) is not None


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: DatabaseSession,
    _: AdminUser,
) -> Customer:
    if _email_exists(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        )
    customer = Customer(**payload.model_dump(), points_balance=0)
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        ) from exc
    db.refresh(customer)
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    db: DatabaseSession,
    _: AdminUser,
) -> Customer:
    customer = _customer_or_404(db, customer_id)
    changes = payload.model_dump(exclude_unset=True)
    email = changes.get("email")
    if isinstance(email, str) and _email_exists(db, email, exclude_id=customer.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        )
    for field, value in changes.items():
        setattr(customer, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        ) from exc
    db.refresh(customer)
    return customer


@router.post("/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: DatabaseSession,
    _: AdminUser,
) -> Transaction:
    customer = _lock_customer_or_404(db, payload.customer_id)
    transaction = Transaction(**payload.model_dump())
    customer.points_balance += payload.points_earned
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/rewards", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
def create_reward(
    payload: RewardCreate,
    db: DatabaseSession,
    _: AdminUser,
) -> Reward:
    customer = _lock_customer_or_404(db, payload.customer_id)
    if customer.points_balance < payload.points_used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer does not have enough points",
        )
    reward = Reward(**payload.model_dump())
    customer.points_balance -= payload.points_used
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward
