import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class CustomerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    loyalty_tier: Literal["Bronze", "Silver", "Gold", "Platinum"]
    join_date: date = Field(default_factory=date.today)

    @field_validator("first_name", "last_name", "city", "email")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return value.upper()


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(
        default=None,
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    loyalty_tier: Literal["Bronze", "Silver", "Gold", "Platinum"] | None = None
    join_date: date | None = None

    @field_validator("first_name", "last_name", "city", "email")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class TransactionRead(APIModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    merchant: str
    category: str
    purchase_amount: Decimal
    points_earned: int
    purchase_date: datetime


class TransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: uuid.UUID
    merchant: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=100)
    purchase_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    points_earned: int = Field(ge=0, le=10_000_000)
    purchase_date: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("merchant", "category")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class RewardRead(APIModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    reward_name: str
    points_used: int
    redeemed_at: datetime


class RewardCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: uuid.UUID
    reward_name: str = Field(min_length=1, max_length=150)
    points_used: int = Field(gt=0, le=10_000_000)
    redeemed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("reward_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


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
    status: Literal["completed", "approval_required"] = "completed"
    workflow_id: str
    classification: Literal["analytics", "sensitive", "out_of_scope"]
    answer: str | None = None
    response_id: str | None = None
    tools_used: list[str]
    approval_request: str | None = None


class AgentApproval(BaseModel):
    approved: bool


class AgentHistoryRead(APIModel):
    id: uuid.UUID
    question: str
    answer: str
    response_id: str
    tools_used: list[str]
    created_at: datetime


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


class IntegrationHealth(BaseModel):
    provider: Literal["postgresql", "snowflake"]
    configured: bool
    connected: bool
    fallback_enabled: bool
    authentication: Literal["key_pair", "password", "unconfigured"]


class SnowflakeSyncResponse(BaseModel):
    status: Literal["synchronized"]
    customers: int = Field(ge=0)
    transactions: int = Field(ge=0)
    rewards: int = Field(ge=0)


class AnalyticsSnapshotRead(APIModel):
    id: uuid.UUID
    object_key: str
    size_bytes: int = Field(ge=0)
    checksum_sha256: str
    created_at: datetime


class AnalyticsSnapshotDownload(BaseModel):
    url: str
    expires_in_seconds: int = Field(ge=60, le=3_600)
