"""Describe the users and saved profile records stored in SQLite."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    """A login account with a private password hash and saved profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    onboarding_step: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    money_details_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Remember when money details were first completed.
    risk_quiz_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Remember when the risk quiz was first completed.
    choices_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Remember when plan choices were first saved.
    plan_review_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Remember when onboarding review was completed.
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


class Profile(Base):
    """One person's income, expenses, savings, debts and goals."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    income: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expenses: Mapped[str | None] = mapped_column(String(30), nullable=True)
    savings: Mapped[str | None] = mapped_column(String(30), nullable=True)
    income_stability: Mapped[str] = mapped_column(String(30), default="steady", nullable=False)  # Remember how much income changes.
    wanted_monthly_amount: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Keep the amount the user wants to invest.
    debts: Mapped[list] = mapped_column(JSON, default=list)
    goals: Mapped[list] = mapped_column(JSON, default=list)
    risk_answers: Mapped[list] = mapped_column(JSON, default=list)
    investor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    user: Mapped[User] = relationship(back_populates="profile")


class InvestmentPlan(Base):
    """One saved plan, its analysis, and the user's first-month checklist."""

    __tablename__ = "investment_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    monthly_amount: Mapped[str] = mapped_column(String(30))
    parts: Mapped[list] = mapped_column(JSON, default=list)
    tax_saving_80c: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tasks: Mapped[list] = mapped_column(JSON, default=list)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class InvestmentLog(Base):
    """One monthly investment amount for one user's goal."""

    __tablename__ = "investment_logs"
    __table_args__ = (
        Index("ix_investment_logs_owner_goal_month", "user_id", "goal_id", "month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(String(36), index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    part_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GoalLogHistory(Base):
    """Audit the old and new values whenever a user's monthly log changes."""

    __tablename__ = "log_history"
    __table_args__ = (
        Index("ix_log_history_owner_log_time", "user_id", "log_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("investment_logs.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    old_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    new_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    old_part_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_part_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    old_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    new_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class GoalValueSnapshot(Base):
    """Keep a dated real-world value entered for a user's goal investments."""

    __tablename__ = "value_snapshots"
    __table_args__ = (
        Index("ix_value_snapshots_owner_goal_time", "user_id", "goal_id", "taken_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(String(36), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ProgressSnapshot(Base):
    """Keep one private, dated summary of a user's financial progress."""

    __tablename__ = "progress_snapshots"
    __table_args__ = (
        Index("ix_progress_snapshots_owner_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    health_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    plan_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    monthly_income: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    monthly_expenses: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    savings: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    money_left_monthly: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    savings_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    debt_to_income: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    emergency_fund_months: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    total_debt: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    total_invested: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    value_today: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    goal_chances: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DashboardResult(Base):
    """The latest saved calculator output displayed by the dashboard and coach."""

    __tablename__ = "dashboard_results"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_dashboard_results_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
