import math
import uuid
from typing import Any, TypeVar, cast

import snowflake.connector
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loyalty_analytics.api.auth import get_current_user
from loyalty_analytics.api.dependencies import DatabaseSession, PageNumber, PageSize
from loyalty_analytics.config import get_settings
from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.schemas import (
    AnalyticsOverview,
    CategoryAnalytics,
    CustomerRead,
    IntegrationHealth,
    LoyaltyTierAnalytics,
    Page,
    RewardAnalytics,
    RewardRead,
    TransactionRead,
)
from loyalty_analytics.services.analytics_backend import (
    SnowflakeAnalyticsBackend,
    get_analytics_backend,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])
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


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverview,
    tags=["Analytics"],
    summary="Get loyalty program KPIs",
)
def analytics_overview(db: DatabaseSession) -> AnalyticsOverview:
    return get_analytics_backend(db).overview()


@router.get(
    "/analytics/loyalty-tiers",
    response_model=list[LoyaltyTierAnalytics],
    tags=["Analytics"],
    summary="Summarize customers by loyalty tier",
)
def analytics_loyalty_tiers(db: DatabaseSession) -> list[LoyaltyTierAnalytics]:
    return get_analytics_backend(db).loyalty_tiers()


@router.get(
    "/analytics/spending-by-category",
    response_model=list[CategoryAnalytics],
    tags=["Analytics"],
    summary="Summarize spending by transaction category",
)
def analytics_spending_categories(db: DatabaseSession) -> list[CategoryAnalytics]:
    return get_analytics_backend(db).spending_categories()


@router.get(
    "/analytics/reward-redemptions",
    response_model=list[RewardAnalytics],
    tags=["Analytics"],
    summary="Summarize reward redemption activity",
)
def analytics_reward_redemptions(db: DatabaseSession) -> list[RewardAnalytics]:
    return get_analytics_backend(db).reward_redemptions()


@router.get(
    "/integrations/snowflake/health",
    response_model=IntegrationHealth,
    tags=["Integrations"],
    summary="Check the configured Snowflake analytics connection",
)
def snowflake_health() -> IntegrationHealth:
    settings = get_settings()
    connected = False
    if settings.snowflake_is_configured:
        try:
            SnowflakeAnalyticsBackend(settings).ping()
            connected = True
        except snowflake.connector.Error:
            connected = False
    return IntegrationHealth(
        provider=settings.analytics_provider,
        configured=settings.snowflake_is_configured,
        connected=connected,
        fallback_enabled=settings.snowflake_fallback_to_postgresql,
        authentication=settings.snowflake_authentication_method,
    )
