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


class AnalyticsOverview(APIModel):
    total_customers: int = Field(ge=0)
    active_customers: int = Field(ge=0)
    total_transactions: int = Field(ge=0)
    total_purchase_amount: Decimal = Field(ge=0, decimal_places=2)
    average_purchase_amount: Decimal = Field(ge=0, decimal_places=2)
    total_points_balance: int = Field(ge=0)
    total_points_earned: int = Field(ge=0)
    total_rewards_redeemed: int = Field(ge=0)
    total_points_redeemed: int = Field(ge=0)


class LoyaltyTierAnalytics(APIModel):
    loyalty_tier: str
    customer_count: int = Field(ge=0)
    total_points_balance: int = Field(ge=0)
    average_points_balance: Decimal = Field(ge=0, decimal_places=2)


class CategoryAnalytics(APIModel):
    category: str
    transaction_count: int = Field(ge=0)
    total_purchase_amount: Decimal = Field(ge=0, decimal_places=2)
    average_purchase_amount: Decimal = Field(ge=0, decimal_places=2)
    total_points_earned: int = Field(ge=0)


class RewardAnalytics(APIModel):
    reward_name: str
    redemption_count: int = Field(ge=0)
    total_points_used: int = Field(ge=0)
    average_points_used: Decimal = Field(ge=0, decimal_places=2)


class AgentQuery(BaseModel):
    question: str = Field(min_length=3, max_length=2_000)


class AgentResponse(BaseModel):
    answer: str
    response_id: str
    tools_used: list[str]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class UserRead(APIModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_admin: bool


class LoginResponse(BaseModel):
    user: UserRead


class Page(APIModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(HealthResponse):
    database: str
