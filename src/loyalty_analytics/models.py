import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from loyalty_analytics.database import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("points_balance >= 0", name="ck_customers_points_balance_nonnegative"),
        Index("ix_customers_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    loyalty_tier: Mapped[str] = mapped_column(String(20))
    points_balance: Mapped[int] = mapped_column(default=0)
    join_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    rewards: Mapped[list["Reward"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("purchase_amount >= 0", name="ck_transactions_amount_nonnegative"),
        CheckConstraint("points_earned >= 0", name="ck_transactions_points_nonnegative"),
        Index("ix_transactions_customer_id", "customer_id"),
        Index("ix_transactions_purchase_date", "purchase_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    merchant: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(100))
    purchase_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    points_earned: Mapped[int]
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    customer: Mapped[Customer] = relationship(back_populates="transactions")


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (
        CheckConstraint("points_used > 0", name="ck_rewards_points_positive"),
        Index("ix_rewards_customer_id", "customer_id"),
        Index("ix_rewards_redeemed_at", "redeemed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    reward_name: Mapped[str] = mapped_column(String(150))
    points_used: Mapped[int]
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    customer: Mapped[Customer] = relationship(back_populates="rewards")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    agent_queries: Mapped[list["AgentQueryHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AgentQueryHistory(Base):
    __tablename__ = "agent_query_history"
    __table_args__ = (Index("ix_agent_query_history_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    response_id: Mapped[str] = mapped_column(String(200))
    tools_used: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="agent_queries")


class AgentWorkflowAudit(Base):
    __tablename__ = "agent_workflow_audit"
    __table_args__ = (Index("ix_agent_workflow_audit_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    classification: Mapped[str] = mapped_column(String(30))
    approved: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    __table_args__ = (Index("ix_analytics_snapshots_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    size_bytes: Mapped[int]
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
