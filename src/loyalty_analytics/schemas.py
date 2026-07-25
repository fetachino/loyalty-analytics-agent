import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerRead(APIModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    city: str
    state: str
    loyalty_tier: str
    points_balance: int
    join_date: date
    created_at: datetime
    updated_at: datetime


class TransactionRead(APIModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    merchant: str
    category: str
    purchase_amount: Decimal
    points_earned: int
    purchase_date: datetime


class RewardRead(APIModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    reward_name: str
    points_used: int
    redeemed_at: datetime


class Page(APIModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class HealthResponse(BaseModel):
    status: str
