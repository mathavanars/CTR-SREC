"""Calculate and persist the user's latest dashboard values."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.calculators import suggest_monthly_amount
from backend.goal_logs import ensure_goal_metadata, get_goal_progress_for_user
from backend.market_data import get_market_snapshot
from backend.models import DashboardResult, InvestmentPlan, Profile, User
from backend.smart_amount import calculate_amount_growth


def _json_safe(value: Any) -> Any:
    """Convert calculator values into JSON values without changing their precision."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _assumptions(projection: dict[str, Any]) -> list[dict[str, str]]:
    """Describe the exact yearly return ranges used by a saved projection."""
    return [
        {
            "idea_id": str(part["idea_id"]),
            "low": str(part["expected_return_low"]),
            "middle": str(part["expected_return_mid"]),
            "high": str(part["expected_return_high"]),
        }
        for part in projection.get("parts", [])
    ]


def _save_result(user: User, db: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Keep one current dashboard calculation row per account."""
    record = (
        db.query(DashboardResult)
        .filter(DashboardResult.user_id == user.id)
        .first()
    )
    if record is None:
        record = DashboardResult(user_id=user.id)
        db.add(record)
    record.result = _json_safe(result)
    record.calculated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record.result


def build_dashboard_result(
    user: User,
    profile: Profile | None,
    db: Session,
) -> dict[str, Any]:
    """Build the dashboard strictly from saved profile, plan and goal-log data."""
    now = datetime.now(timezone.utc)
    if profile is None or profile.income is None or profile.expenses is None:
        missing = []
        if profile is None or profile.income is None:
            missing.append("monthly income")
        if profile is None or profile.expenses is None:
            missing.append("monthly expenses")
        return _save_result(user, db, {
            "profile_complete": False,
            "missing_profile_fields": missing,
            "investable_amount": None,
            "expense_limit": None,
            "scenarios": [],
            "goals": [],
            "debts": [],
            "growth": None,
            "growth_missing_reason": "Save your income and expenses first.",
            "calculated_at": now.isoformat(),
        })

    plan = (
        db.query(InvestmentPlan)
        .filter(InvestmentPlan.user_id == user.id)
        .first()
    )
    profile_data = {
        "income": profile.income,
        "expenses": profile.expenses or "0",
        "savings": profile.savings or "0",
        "debts": profile.debts or [],
        "goals": profile.goals or [],
        "income_stability": profile.income_stability,
        "wanted_monthly_amount": profile.wanted_monthly_amount,
        "investor_type": profile.investor_type or "balanced",
    }
    suggestion = suggest_monthly_amount(profile_data)
    snapshot = get_market_snapshot()
    saved_parts = plan.parts if plan is not None and not plan.is_stale else None
    investable_amount = (
        str(suggestion["recommended"])
        if suggestion["ready_to_invest"]
        else None
    )

    expense_limit = None
    if investable_amount is not None:
        expense_result = calculate_amount_growth(
            investable_amount,
            5,
            profile_data,
            saved_parts,
            snapshot,
        )
        if expense_result["mode"] == "growth":
            expense_limit = expense_result["expense_limit"]

    saved_amount = (
        plan.monthly_amount
        if plan is not None
        else profile.wanted_monthly_amount
    )
    growth = None
    growth_missing_reason = None
    growth_two_years = None
    if saved_amount is None or Decimal(str(saved_amount)) <= 0:
        growth_missing_reason = "Save a monthly amount to see a growth estimate."
    elif plan is not None and plan.is_stale:
        growth_missing_reason = "Re-check your saved plan before viewing a growth estimate."
    else:
        projection = calculate_amount_growth(
            saved_amount,
            5,
            profile_data,
            saved_parts,
            snapshot,
        )
        if projection["mode"] == "growth":
            growth = {
                "amount": projection["amount"],
                "years": 5,
                "totals": projection["totals"],
                "series": projection["series"][:5],
                "assumptions": _assumptions(projection),
                "label": "Estimate",
            }
        else:
            growth_missing_reason = projection["message"]

        two_year_projection = calculate_amount_growth(
            saved_amount,
            2,
            profile_data,
            saved_parts,
            snapshot,
        )
        if two_year_projection["mode"] == "growth":
            growth_two_years = {
                "amount": two_year_projection["amount"],
                "years": 2,
                "totals": two_year_projection["totals"],
                "assumptions": _assumptions(two_year_projection),
                "label": "Estimate",
            }

    goals = ensure_goal_metadata(profile, user)
    if db.is_modified(profile):
        db.commit()
    goal_progress = [
        get_goal_progress_for_user(str(goal["id"]), user, db)
        for goal in goals
    ]
    scenarios = [
        {"label": "Stretch", "amount": str(suggestion["stretch"])},
        {
            "label": "You want",
            "amount": (
                str(profile.wanted_monthly_amount)
                if profile.wanted_monthly_amount is not None
                else None
            ),
        },
    ]
    result = {
        "profile_complete": True,
        "missing_profile_fields": [],
        "investable_amount": investable_amount,
        "investment_ready": bool(suggestion["ready_to_invest"]),
        "investment_note": (
            None
            if suggestion["ready_to_invest"]
            else "Build your emergency fund or pay high-interest debt before investing."
        ),
        "expense_limit": expense_limit,
        "scenarios": scenarios,
        "own_amount": profile.wanted_monthly_amount,
        "goals": goal_progress,
        "debts": profile.debts or [],
        "growth": growth,
        "growth_missing_reason": growth_missing_reason,
        "growth_two_years": growth_two_years,
        "saved_monthly_amount": saved_amount,
        "calculated_at": now.isoformat(),
    }
    return _save_result(user, db, result)
