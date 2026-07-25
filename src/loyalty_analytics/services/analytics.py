from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loyalty_analytics.models import Customer, Reward, Transaction
from loyalty_analytics.schemas import (
    AnalyticsOverview,
    CategoryAnalytics,
    LoyaltyTierAnalytics,
    RewardAnalytics,
)

ZERO = Decimal("0.00")


def _two_decimal_places(value: object) -> Decimal:
    return Decimal(str(value or ZERO)).quantize(Decimal("0.01"))


def get_overview(db: Session) -> AnalyticsOverview:
    """Return platform-wide customer, transaction, and reward KPIs."""
    customer_count, points_balance = db.execute(
        select(func.count(Customer.id), func.coalesce(func.sum(Customer.points_balance), 0))
    ).one()
    transaction_count, active_customers, revenue, points_earned, average_purchase = db.execute(
        select(
            func.count(Transaction.id),
            func.count(func.distinct(Transaction.customer_id)),
            func.coalesce(func.sum(Transaction.purchase_amount), 0),
            func.coalesce(func.sum(Transaction.points_earned), 0),
            func.coalesce(func.avg(Transaction.purchase_amount), 0),
        )
    ).one()
    reward_count, points_redeemed = db.execute(
        select(func.count(Reward.id), func.coalesce(func.sum(Reward.points_used), 0))
    ).one()

    return AnalyticsOverview(
        total_customers=customer_count,
        active_customers=active_customers,
        total_transactions=transaction_count,
        total_purchase_amount=_two_decimal_places(revenue),
        average_purchase_amount=_two_decimal_places(average_purchase),
        total_points_balance=points_balance,
        total_points_earned=points_earned,
        total_rewards_redeemed=reward_count,
        total_points_redeemed=points_redeemed,
    )


def get_loyalty_tiers(db: Session) -> list[LoyaltyTierAnalytics]:
    """Aggregate customer membership and point balances by loyalty tier."""
    statement = (
        select(
            Customer.loyalty_tier,
            func.count(Customer.id).label("customer_count"),
            func.coalesce(func.sum(Customer.points_balance), 0).label("total_points_balance"),
            func.coalesce(func.avg(Customer.points_balance), 0).label("average_points_balance"),
        )
        .group_by(Customer.loyalty_tier)
        .order_by(Customer.loyalty_tier)
    )
    return [
        LoyaltyTierAnalytics(
            loyalty_tier=row.loyalty_tier,
            customer_count=row.customer_count,
            total_points_balance=row.total_points_balance,
            average_points_balance=_two_decimal_places(row.average_points_balance),
        )
        for row in db.execute(statement)
    ]


def get_spending_categories(db: Session) -> list[CategoryAnalytics]:
    """Aggregate purchase behavior by transaction category."""
    statement = (
        select(
            Transaction.category,
            func.count(Transaction.id).label("transaction_count"),
            func.sum(Transaction.purchase_amount).label("total_purchase_amount"),
            func.avg(Transaction.purchase_amount).label("average_purchase_amount"),
            func.sum(Transaction.points_earned).label("total_points_earned"),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.purchase_amount).desc(), Transaction.category)
    )
    return [
        CategoryAnalytics(
            category=row.category,
            transaction_count=row.transaction_count,
            total_purchase_amount=_two_decimal_places(row.total_purchase_amount),
            average_purchase_amount=_two_decimal_places(row.average_purchase_amount),
            total_points_earned=row.total_points_earned,
        )
        for row in db.execute(statement)
    ]


def get_reward_redemptions(db: Session) -> list[RewardAnalytics]:
    """Aggregate redemption usage by reward name."""
    statement = (
        select(
            Reward.reward_name,
            func.count(Reward.id).label("redemption_count"),
            func.sum(Reward.points_used).label("total_points_used"),
            func.avg(Reward.points_used).label("average_points_used"),
        )
        .group_by(Reward.reward_name)
        .order_by(func.count(Reward.id).desc(), Reward.reward_name)
    )
    return [
        RewardAnalytics(
            reward_name=row.reward_name,
            redemption_count=row.redemption_count,
            total_points_used=row.total_points_used,
            average_points_used=_two_decimal_places(row.average_points_used),
        )
        for row in db.execute(statement)
    ]
