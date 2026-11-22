"""Build private, number-backed reports and create downloadable PDF and CSV files."""

import csv
import io
import json
import logging
import re
import time
from calendar import monthrange
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from backend.app_config import APP_CREDIT, APP_VERSION
from backend.analysis import analyze_plan
from backend.auth import get_current_user
from backend.calculators import (
    calculate_debt_payoff,
    calculate_debt_to_income_ratio,
    calculate_emergency_fund_months,
    calculate_health_score,
    calculate_lump_sum_future_value,
    calculate_money_left_after_debts,
    calculate_plan_growth,
    calculate_readiness,
    calculate_savings_rate,
    calculate_sip_future_value,
    calculate_sip_future_value_months,
    calculate_required_monthly_sip,
    calculate_goal_chance,
    split_monthly_amount,
    suggest_monthly_amount,
)
from backend.database import get_db
from backend.investment_ideas import load_basics_jars, load_investment_ideas
from backend.market_data import get_market_snapshot
from backend.models import (
    GoalLogHistory,
    InvestmentLog,
    InvestmentPlan,
    Profile,
    ProgressSnapshot,
    User,
)
from backend.smart_amount import calculate_amount_growth
from backend.suggestion_config import ASSET_RISK, STRESS_SHOCKS


router = APIRouter()
LOGGER = logging.getLogger(__name__)
ZERO = Decimal("0")
HUNDRED = Decimal("100")
PAISE = Decimal("0.01")
INDIA = ZoneInfo("Asia/Kolkata")
PDF_ATTEMPTS: dict[int, deque[float]] = {}
PDF_LIMIT = 5
PDF_WINDOW_SECONDS = 60
PDF_FONTS_READY = False
DISCLAIMER = (
    "Educational guidance only. Not licensed financial advice. "
    "Investments carry risk. Returns are not guaranteed."
)
PERIOD_LABELS = {
    "last_month": "Last month",
    "last_3_months": "Last 3 months",
    "last_6_months": "Last 6 months",
    "since_started": "Since I started",
}

# Keep warning thresholds and user-facing explanations together for easy review.
WARNING_RULES = [
    {"id": "emergency-fund", "metric": "emergency_fund_months", "operator": "lt", "threshold": Decimal("3"), "severity": "Problem", "what": "Your emergency fund is under 3 months.", "why": "A surprise bill could be hard to pay.", "action": "Build your emergency fund before taking more investment risk."},
    {"id": "high-interest-debt", "metric": "max_interest_rate", "operator": "gt", "threshold": Decimal("15"), "severity": "Problem", "what": "You have debt above 15% interest.", "why": "High interest can grow faster than savings.", "action": "Try to pay the highest-interest debt first."},
    {"id": "debt-to-income", "metric": "debt_to_income", "operator": "gt", "threshold": Decimal("40"), "severity": "Problem", "what": "Your debt payments are above 40% of income.", "why": "Large payments leave less room for other needs.", "action": "Review your monthly EMI and spending."},
    {"id": "low-savings-rate", "metric": "savings_rate", "operator": "lt", "threshold": Decimal("10"), "severity": "Watch", "what": "Your savings rate is under 10%.", "why": "A small saving amount can make goals take longer.", "action": "Choose one expense to reduce and save that amount."},
    {"id": "risk-fit", "metric": "plan_risk_ok", "operator": "false", "threshold": ZERO, "severity": "Watch", "what": "Your plan risk is outside your investor-type range.", "why": "The plan may feel too risky or too cautious.", "action": "Re-check the plan against your comfort level."},
    {"id": "short-goal-equity", "metric": "short_goal_equity", "operator": "true", "threshold": ZERO, "severity": "Problem", "what": "A goal is under 3 years away and equity is above 30%.", "why": "Share prices can fall just before you need the money.", "action": "Keep near-term goal money in safer choices."},
    {"id": "locked-money", "metric": "locked_money", "operator": "true", "threshold": ZERO, "severity": "Watch", "what": "More than half your plan is locked and a goal is under 5 years away.", "why": "You may not be able to take the money out in time.", "action": "Keep enough near-term goal money easy to access."},
    {"id": "behind-plan", "metric": "behind_percent", "operator": "lt", "threshold": Decimal("-10"), "severity": "Watch", "what": "Your real investments are more than 10% behind the plan.", "why": "You may need to add more or change the goal date.", "action": "Check your catch-up amount and update your plan."},
    {"id": "missed-months", "metric": "missed_recent_months", "operator": "gte", "threshold": Decimal("2"), "severity": "Watch", "what": "You missed at least 2 of the last 3 months.", "why": "Missed months can slow your progress.", "action": "Set a reminder for your next monthly update."},
    {"id": "low-goal-chance", "metric": "lowest_goal_chance", "operator": "lt", "threshold": Decimal("50"), "severity": "Watch", "what": "A goal's chance with real investments is under 50%.", "why": "The current path may not reach the full target.", "action": "Review the goal amount, date, and monthly amount."},
    {"id": "old-market-data", "metric": "market_age_days", "operator": "gt", "threshold": Decimal("7"), "severity": "Watch", "what": "Market data is more than 7 days old.", "why": "Rates and market figures may have changed.", "action": "Refresh the market data before using it."},
]


def _now_utc() -> datetime:
    """Return one timezone-aware UTC time for saved report history."""
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """Treat old SQLite timestamps as UTC and normalize every saved time."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _decimal(value: object, default: Decimal = ZERO) -> Decimal:
    """Convert saved values to Decimal without using browser-style floats."""
    if value is None or value == "":
        return default
    return Decimal(str(value))


def _money(value: object) -> str:
    """Round a final money amount to paise and return a JSON-safe string."""
    return str(_decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP))


def _number(value: object, places: str = "0.01") -> str | None:
    """Round a final display number to a clear number of decimal places."""
    if value is None:
        return None
    return str(_decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def _format_time(value: datetime | None) -> str | None:
    """Show one saved UTC timestamp in the user's default India timezone."""
    normalized = _as_utc(value)
    if normalized is None:
        return None
    local_time = normalized.astimezone(INDIA)
    return (
        f"{local_time.strftime('%d %b %Y')}, "
        f"{local_time.strftime('%I:%M %p').lstrip('0')}"
    )


def _format_date(value: datetime | date | None) -> str | None:
    """Show a stored time or date using a short India-friendly date."""
    if isinstance(value, datetime):
        normalized = _as_utc(value)
        return normalized.astimezone(INDIA).strftime("%d %b %Y") if normalized else None
    return value.strftime("%d %b %Y") if value else None


def _jsonable(value: Any) -> Any:
    """Turn Decimal and date values into safe JSON values recursively."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _subtract_months(value: datetime, months: int) -> datetime:
    """Move a date back by whole calendar months without changing its timezone."""
    month_index = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _period_start(user: User, period: str, now: datetime) -> datetime:
    """Choose the UTC beginning for one of the four report periods."""
    local_now = now.astimezone(INDIA)
    if period == "last_month":
        start = _subtract_months(local_now, 1)
    elif period == "last_3_months":
        start = _subtract_months(local_now, 3)
    elif period == "last_6_months":
        start = _subtract_months(local_now, 6)
    else:
        start = _as_utc(user.created_at) or now
    return start.astimezone(timezone.utc)


def _catalog() -> dict[str, dict[str, Any]]:
    """Make one trusted lookup for investment ideas and basic safety jars."""
    return {
        str(item["id"]): item
        for item in load_investment_ideas() + load_basics_jars()
    }


def _saved_plan_parts(plan: InvestmentPlan | None) -> list[dict[str, Any]]:
    """Attach catalog facts and exact monthly rupees to the user's chosen parts."""
    if plan is None:
        return []
    saved = [part for part in (plan.parts or []) if _decimal(part.get("share")) > ZERO]
    if not saved:
        return []
    amounts = split_monthly_amount(
        plan.monthly_amount,
        [part.get("share", 0) for part in saved],
    )
    catalog = _catalog()
    result = []
    for saved_part, amount in zip(saved, amounts):
        idea_id = str(saved_part.get("idea_id", ""))
        idea = catalog.get(idea_id)
        if idea is None:
            raise HTTPException(
                status_code=409,
                detail="A saved investment choice is no longer available. Please edit and save your plan again.",
            )
        result.append({
            "idea_id": idea_id,
            "name": str(idea["name"]),
            "asset_class": str(idea["asset_class"]),
            "share": _number(saved_part.get("share")),
            "monthly_amount": _money(amount),
            "risk_level": int(idea["risk_level"]),
            "risk_words": str(idea["risk_words"]),
            "expected_return_low": _number(idea["expected_return_low"]),
            "expected_return_mid": _number(idea["expected_return_mid"]),
            "expected_return_high": _number(idea["expected_return_high"]),
            "minimum_to_start": _money(idea["minimum_to_start"]),
        })
    return result


def _snapshot_current(user: User, db: Session) -> ProgressSnapshot:
    """Save a private point-in-time summary after a user's progress changes."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user.id).first()
    fields: dict[str, Any] = {
        "health_score": None,
        "plan_score": None,
        "monthly_income": None,
        "monthly_expenses": None,
        "savings": None,
        "money_left_monthly": None,
        "savings_rate": None,
        "debt_to_income": None,
        "emergency_fund_months": None,
        "total_debt": ZERO,
        "total_invested": ZERO,
        "value_today": ZERO,
        "goal_chances": {},
    }
    goals: list[dict[str, Any]] = []
    if profile is not None:
        from backend.goal_logs import ensure_goal_metadata, get_goal_progress_for_user

        goals = ensure_goal_metadata(profile, user)
    if profile is not None and profile.income:
        income = _decimal(profile.income)
        expenses = _decimal(profile.expenses)
        savings = _decimal(profile.savings)
        debts = profile.debts or []
        health = calculate_health_score(
            income, expenses, savings, debts, profile.goals or [],
        )
        readiness = calculate_readiness(income, expenses, savings, debts)
        emis = sum((_decimal(debt.get("emi")) for debt in debts), ZERO)
        fields.update({
            "health_score": Decimal(str(health["score"])),
            "monthly_income": income,
            "monthly_expenses": expenses,
            "savings": savings,
            "money_left_monthly": calculate_money_left_after_debts(income, expenses, debts),
            "savings_rate": calculate_savings_rate(income, expenses),
            "debt_to_income": calculate_debt_to_income_ratio(emis, income),
            "emergency_fund_months": calculate_emergency_fund_months(savings, expenses),
            "total_debt": sum((_decimal(debt.get("amount", debt.get("balance"))) for debt in debts), ZERO),
        })
        if plan is not None and plan.parts and profile.investor_type:
            try:
                analysis = analyze_plan(
                    {
                        "income": income,
                        "expenses": expenses,
                        "savings": savings,
                        "debts": debts,
                        "goals": profile.goals or [],
                        "investor_type": profile.investor_type,
                    },
                    {"monthly_amount": plan.monthly_amount, "parts": plan.parts},
                )
                fields["plan_score"] = Decimal(str(analysis["score"]))
            except (ValueError, KeyError) as error:
                LOGGER.warning("Could not score the saved plan in a report snapshot: %s", error)
                fields["plan_score"] = None
    for goal in goals:
        progress = get_goal_progress_for_user(str(goal["id"]), user, db)
        fields["total_invested"] += _decimal(progress.get("total_invested"))
        fields["value_today"] += _decimal(progress.get("value_today"))
        fields["goal_chances"][str(goal["id"])] = {
            "name": str(goal["name"]),
            "chance": _money(progress.get("chance_with_real_investments")),
        }
    snapshot = ProgressSnapshot(user_id=user.id, created_at=_now_utc(), **fields)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def record_progress_snapshot(user: User, db: Session) -> ProgressSnapshot:
    """Save a new report snapshot after an important profile or plan change."""
    return _snapshot_current(user, db)


def _ensure_monthly_snapshot(user: User, db: Session, now: datetime) -> None:
    """Add at most one snapshot in the current UTC month when a report is opened."""
    latest = (
        db.query(ProgressSnapshot)
        .filter(ProgressSnapshot.user_id == user.id)
        .order_by(ProgressSnapshot.created_at.desc(), ProgressSnapshot.id.desc())
        .first()
    )
    latest_time = _as_utc(latest.created_at) if latest is not None else None
    if latest_time is None or (latest_time.year, latest_time.month) != (now.year, now.month):
        _snapshot_current(user, db)


def _snapshot_value(snapshot: ProgressSnapshot | None, name: str) -> Decimal | None:
    """Read one optional number from a saved comparison snapshot."""
    if snapshot is None:
        return None
    value = getattr(snapshot, name)
    return _decimal(value) if value is not None else None


def _change_row(
    label: str,
    past: Decimal | None,
    present: Decimal | None,
    favorable_low: bool = False,
) -> dict[str, Any]:
    """Compare two saved Decimal values and mark the direction of change."""
    if past is None or present is None:
        return {"item": label, "past": None, "present": _money(present) if present is not None else None, "change": None, "change_percent": None, "arrow": "same"}
    change = present - past
    percent = (change / past * HUNDRED) if past != ZERO else None
    is_better = change < ZERO if favorable_low else change > ZERO
    arrow = "same" if change == ZERO else ("better" if is_better else "worse")
    return {
        "item": label,
        "past": _money(past),
        "present": _money(present),
        "change": _money(change),
        "change_percent": _number(percent) if percent is not None else "New",
        "arrow": arrow,
    }


def _snapshot_comparison(
    past: ProgressSnapshot | None,
    present: ProgressSnapshot | None,
) -> list[dict[str, Any]]:
    """Build the required past-versus-present rows from the saved snapshots."""
    definitions = [
        ("Health score", "health_score", False),
        ("Plan score", "plan_score", False),
        ("Savings", "savings", False),
        ("Total debt", "total_debt", True),
        ("Money left each month", "money_left_monthly", False),
        ("Emergency fund months", "emergency_fund_months", False),
        ("Total invested", "total_invested", False),
        ("Value today", "value_today", False),
    ]
    rows = [
        _change_row(
            label,
            _snapshot_value(past, field),
            _snapshot_value(present, field),
            favorable_low,
        )
        for label, field, favorable_low in definitions
    ]
    past_goals = past.goal_chances or {} if past is not None else {}
    present_goals = present.goal_chances or {} if present is not None else {}
    for goal_id in sorted(set(past_goals) | set(present_goals)):
        earlier = past_goals.get(goal_id, {})
        current = present_goals.get(goal_id, {})
        name = str(current.get("name") or earlier.get("name") or "Goal")
        rows.append(_change_row(
            f"Goal chance: {name}",
            _decimal(earlier.get("chance")) if earlier.get("chance") is not None else None,
            _decimal(current.get("chance")) if current.get("chance") is not None else None,
        ))
    return rows


def _plan_analysis(
    profile: Profile | None,
    plan: InvestmentPlan | None,
) -> dict[str, Any] | None:
    """Re-check a saved plan using the user's current profile and choices."""
    if profile is None or plan is None or not plan.parts or not profile.income or not profile.investor_type:
        return None
    try:
        return analyze_plan(
            {
                "income": profile.income,
                "expenses": profile.expenses or "0",
                "savings": profile.savings or "0",
                "debts": profile.debts or [],
                "goals": profile.goals or [],
                "investor_type": profile.investor_type,
            },
            {"monthly_amount": plan.monthly_amount, "parts": plan.parts},
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(
            status_code=409,
            detail="The saved plan could not be checked. Please edit and save your plan again.",
        ) from error


def _goal_report_rows(user: User, db: Session, profile: Profile | None) -> list[dict[str, Any]]:
    """Build each goal's saved progress from this user's private goal records."""
    if profile is None:
        return []
    from backend.goal_logs import ensure_goal_metadata, get_goal_progress_for_user

    rows = []
    for goal in ensure_goal_metadata(profile, user):
        progress = get_goal_progress_for_user(str(goal["id"]), user, db)
        rows.append({
            "id": str(goal["id"]),
            "name": str(goal["name"]),
            "target": _money(goal["amount"]),
            "years_left": int(goal["years"]),
            "invested": _money(progress["total_invested"]),
            "value_today": _money(progress["value_today"]),
            "value_label": str(progress["value_label"]),
            "planned_by_now": _money(progress["expected_by_now"]),
            "ahead_behind": _money(progress["ahead_behind"]),
            "ahead_behind_percent": _number(progress["ahead_behind_percent"]),
            "direction": str(progress["ahead_behind_direction"]),
            "chance_now": _number(progress["chance_with_real_investments"]),
            "chance_with_plan": _number(progress["chance_with_plan"]),
            "catch_up_monthly": _money(progress["catch_up_monthly"]) if progress["catch_up_monthly"] is not None else None,
            "next_step": str(progress["next_step"]),
            "streak_months": int(progress["streak_months"]),
            "consistency_percent": _number(progress["consistency_percent"]),
            "last_updated": _format_time(progress["last_updated"]),
            "current_month_logged": bool(progress["current_month_logged"]),
            "months_passed": int(progress["months_passed"]),
            "months_left": int(progress["remaining_months"]),
            "chart": _goal_chart_data(goal, progress, user, db),
        })
    return rows


def _goal_chart_data(goal: Mapping[str, Any], progress: Mapping[str, Any], user: User, db: Session) -> dict[str, Any]:
    """Build the planned and real contribution lines for one goal."""
    logs = (
        db.query(InvestmentLog)
        .filter(
            InvestmentLog.user_id == user.id,
            InvestmentLog.goal_id == str(goal["id"]),
            InvestmentLog.deleted_at.is_(None),
        )
        .order_by(InvestmentLog.month.asc(), InvestmentLog.id.asc())
        .all()
    )
    actual_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for log in logs:
        actual_by_month[log.month.strftime("%Y-%m")] += _decimal(log.amount)
    start = date.fromisoformat(str(goal["start_date"]))
    count = max(1, int(progress["months_passed"]))
    labels = []
    planned_values = []
    actual_values = []
    planned_amount = _decimal(progress.get("planned_monthly_amount"))
    planned_total = ZERO
    actual_total = ZERO
    for index in range(count):
        month_index = start.year * 12 + start.month - 1 + index
        year, month_zero = divmod(month_index, 12)
        key = f"{year:04d}-{month_zero + 1:02d}"
        labels.append(key)
        planned_total += planned_amount
        actual_total += actual_by_month.get(key, ZERO)
        planned_values.append(_money(planned_total))
        actual_values.append(_money(actual_total))
    return {"labels": labels, "planned": planned_values, "actual": actual_values}


def _debt_report(profile: Profile | None, today: date) -> dict[str, Any]:
    """Summarize debts, payoff comparisons, interest and a balance timeline."""
    debts = list(profile.debts or []) if profile is not None else []
    rows = []
    normalized_debts = []
    for index, debt in enumerate(debts):
        normalized = {
            "name": str(debt.get("name") or f"Debt {index + 1}"),
            "amount": str(debt.get("amount", debt.get("balance", "0"))),
            "interest_rate": str(debt.get("interest_rate", debt.get("annual_rate", "0"))),
            "emi": str(debt.get("emi", debt.get("monthly_emi", "0"))),
        }
        normalized_debts.append(normalized)
        try:
            payoff = calculate_debt_payoff([normalized], "avalanche")
            months_left = int(payoff["months"])
            interest_left = _money(payoff["total_interest_paid"])
        except ValueError:
            months_left = None
            interest_left = None
        rows.append({
            "name": normalized["name"],
            "balance": _money(normalized["amount"]),
            "interest_rate": _number(normalized["interest_rate"]),
            "emi": _money(normalized["emi"]),
            "months_left": months_left,
            "interest_left": interest_left,
        })
    try:
        avalanche = calculate_debt_payoff(normalized_debts, "avalanche")
        snowball = calculate_debt_payoff(normalized_debts, "snowball")
    except ValueError:
        avalanche = {"months": None, "total_interest_paid": None, "schedule": []}
        snowball = {"months": None, "total_interest_paid": None, "schedule": []}
    schedule = avalanche["schedule"]
    labels = [str(item["month"]) for item in schedule]
    balances = [
        _money(sum((_decimal(value) for value in item["balances"].values()), ZERO))
        for item in schedule
    ]
    total_balance = sum((_decimal(debt["amount"]) for debt in normalized_debts), ZERO)
    def payoff_date(months: object) -> str | None:
        """Return the estimated debt-free month when the calculator has a schedule."""
        if months is None:
            return None
        month_index = today.year * 12 + today.month - 1 + int(months)
        year, month_zero = divmod(month_index, 12)
        return date(year, month_zero + 1, 1).strftime("%b %Y")
    return {
        "items": rows,
        "total_balance": _money(total_balance),
        "avalanche": {
            "months": avalanche["months"],
            "interest": _money(avalanche["total_interest_paid"]) if avalanche["total_interest_paid"] is not None else None,
            "debt_free_date": payoff_date(avalanche["months"]),
        },
        "snowball": {
            "months": snowball["months"],
            "interest": _money(snowball["total_interest_paid"]) if snowball["total_interest_paid"] is not None else None,
            "debt_free_date": payoff_date(snowball["months"]),
        },
        "chart": {"labels": labels, "balance": balances},
        "empty": not rows,
    }


def _investment_logs(
    user: User,
    db: Session,
    plan_monthly: Decimal,
    parts: list[dict[str, Any]],
    today: date,
) -> dict[str, Any]:
    """Return the latest year of owner-only investment log history and totals."""
    since_month = today.year * 12 + today.month - 1 - 11
    since_year, since_month_zero = divmod(since_month, 12)
    since_date = date(since_year, since_month_zero + 1, 1)
    logs = (
        db.query(InvestmentLog)
        .filter(InvestmentLog.user_id == user.id, InvestmentLog.month >= since_date)
        .order_by(InvestmentLog.updated_at.desc(), InvestmentLog.id.desc())
        .all()
    )
    history_rows = []
    if logs:
        log_ids = [log.id for log in logs]
        history = (
            db.query(GoalLogHistory)
            .filter(
                GoalLogHistory.user_id == user.id,
                GoalLogHistory.log_id.in_(log_ids),
            )
            .order_by(GoalLogHistory.changed_at.desc(), GoalLogHistory.id.desc())
            .all()
        )
        action_by_id: dict[int, list[str]] = defaultdict(list)
        for row in history:
            action_by_id[row.log_id].append(row.action)
    else:
        action_by_id = defaultdict(list)
    catalog = _catalog()
    active_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for log in logs:
        month_label = log.month.strftime("%Y-%m")
        if log.deleted_at is None:
            active_by_month[month_label] += _decimal(log.amount)
        if log.deleted_at is not None:
            status = "Deleted"
        elif "Edited" in action_by_id.get(log.id, []):
            status = "Edited"
        else:
            status = "Added"
        history_rows.append({
            "date_time": _format_time(log.updated_at),
            "month": month_label,
            "amount": _money(log.amount),
            "part": catalog.get(str(log.part_id), {}).get("name") if log.part_id else None,
            "note": log.note,
            "status": status,
        })
    chart_labels = []
    planned_values = []
    actual_values = []
    for offset in range(12):
        month_index = since_date.year * 12 + since_date.month - 1 + offset
        year, month_zero = divmod(month_index, 12)
        label = f"{year:04d}-{month_zero + 1:02d}"
        chart_labels.append(label)
        planned_values.append(_money(plan_monthly))
        actual_values.append(_money(active_by_month.get(label, ZERO)))
    actual_total = sum(active_by_month.values(), ZERO)
    return {
        "items": history_rows,
        "planned_last_12_months": _money(plan_monthly * Decimal("12")),
        "actual_last_12_months": _money(actual_total),
        "empty": not history_rows,
        "chart": {
            "labels": chart_labels,
            "planned": planned_values,
            "actual": actual_values,
        },
    }


def _scenario_rate(part: Mapping[str, Any], scenario: str) -> Decimal:
    """Read a saved scenario rate for one chosen plan part."""
    key = "mid" if scenario == "middle" else scenario
    return _decimal(part.get(f"expected_return_{key}"))


def _grown_current_value(value: Decimal, parts: list[dict[str, Any]], scenario: str, years: int) -> Decimal:
    """Grow current money separately through every chosen plan part."""
    if years == 0:
        return value.quantize(PAISE, rounding=ROUND_HALF_UP)
    if not parts:
        return calculate_lump_sum_future_value(value, ZERO, years)
    total = ZERO
    for part in parts:
        allocated = value * _decimal(part["share"]) / HUNDRED
        total += calculate_lump_sum_future_value(
            allocated,
            _scenario_rate(part, scenario),
            years,
        )
    return total.quantize(PAISE, rounding=ROUND_HALF_UP)


def _future_outlook(
    parts: list[dict[str, Any]],
    monthly_amount: Decimal,
    current_value: Decimal,
    total_invested: Decimal,
    goals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build low, middle and high futures by calculating every part separately."""
    years_list = [1, 3, 5, 10]
    rows = []
    for years in years_list:
        growth = calculate_plan_growth(parts, years) if parts else {
            "low": ZERO, "mid": ZERO, "high": ZERO, "invested": ZERO,
        }
        invested = total_invested + monthly_amount * Decimal(years * 12)
        scenarios = {}
        for scenario in ("low", "mid", "high"):
            future = _grown_current_value(current_value, parts, scenario, years) + _decimal(growth[scenario])
            scenarios[scenario] = {
                "value": _money(future),
                "invested": _money(invested),
                "earned": _money(future - invested),
            }
        rows.append({"years": years, **scenarios})
    curve_labels = list(range(0, 31))
    curves = {"follow_plan": [], "invested_so_far": [], "stop_investing": []}
    for years in curve_labels:
        if years == 0:
            follow = current_value
            invested_so_far = total_invested
            stopped = current_value
        else:
            future = calculate_plan_growth(parts, years) if parts else {"mid": ZERO}
            follow = _grown_current_value(current_value, parts, "mid", years) + _decimal(future["mid"])
            invested_so_far = _grown_current_value(total_invested, parts, "mid", years)
            stopped = _grown_current_value(current_value, parts, "mid", years)
        curves["follow_plan"].append(_money(follow))
        curves["invested_so_far"].append(_money(invested_so_far))
        curves["stop_investing"].append(_money(stopped))
    stress_percent = ZERO
    for part in parts:
        asset_class = str(part["asset_class"]).lower()
        class_key = (
            "equity" if "equity" in asset_class
            else "gold" if "gold" in asset_class
            else "no_drop" if part["idea_id"] in {"ppf", "fd-rd", "savings-liquid", "nps"}
            else "debt-fund" if "debt" in asset_class
            else "no_drop"
        )
        shock = Decimal(str(STRESS_SHOCKS.get(class_key, 0)))
        stress_percent += _decimal(part["share"]) * max(ZERO, -shock) / HUNDRED
    stress_loss = current_value * stress_percent / HUNDRED
    goal_forecasts = []
    for goal in goals:
        forecast = {}
        target = _decimal(goal["target"])
        for scenario in ("low", "mid", "high"):
            reached_year = None
            chance = ZERO
            for years in range(1, 31):
                growth = calculate_plan_growth(parts, years) if parts else {"low": ZERO, "mid": ZERO, "high": ZERO}
                value = _grown_current_value(_decimal(goal["value_today"]), parts, scenario, years) + _decimal(growth[scenario])
                chance = calculate_goal_chance(value, target)
                if value >= target:
                    reached_year = years
                    break
            forecast[scenario] = {
                "chance_percent": _number(chance),
                "year_reached": reached_year,
            }
        goal_forecasts.append({"goal": goal["name"], **forecast})
    return {
        "rows": rows,
        "curve": {
            "years": curve_labels,
            **curves,
            "goal_target": _money(goals[0]["target"]) if goals else None,
            "goal_name": goals[0]["name"] if goals else None,
        },
        "goal_forecasts": goal_forecasts,
        "stress_test": {
            "fall_percent": _number(stress_percent),
            "loss": _money(stress_loss),
            "label": "These are possible outcomes, not predictions or promises.",
        },
        "empty": not parts,
    }


def _market_data() -> dict[str, Any] | None:
    """Return public market values with source links when a saved snapshot exists."""
    snapshot = get_market_snapshot()
    metrics = snapshot.get("metrics") or {}
    if not metrics:
        return None
    names = {
        "cpi_inflation": "India CPI inflation",
        "repo_rate": "RBI repo rate",
        "sbi_1y_fd_rate": "SBI 1-year FD rate",
        "ppf_rate": "PPF rate",
        "government_10y_yield": "10-year government bond yield",
    }
    rows = []
    for key, label in names.items():
        metric = metrics.get(key)
        if not metric:
            continue
        rows.append({
            "name": label,
            "value": str(metric.get("value")),
            "direction": metric.get("direction"),
            "source_url": metric.get("source_url"),
            "fetched_at": metric.get("fetched_at"),
        })
    return {
        "data_as_of": snapshot.get("data_as_of"),
        "message": snapshot.get("message"),
        "items": rows,
        "stale_metrics": snapshot.get("stale_metrics") or [],
    }


def _market_age(market: dict[str, Any] | None, now: datetime) -> Decimal | None:
    """Find how old the saved market snapshot is in whole days."""
    if market is None or not market.get("data_as_of"):
        return None
    try:
        snapshot_date = date.fromisoformat(str(market["data_as_of"])[:10])
    except ValueError:
        return None
    return Decimal((now.astimezone(INDIA).date() - snapshot_date).days)


def _warning_items(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Apply the one shared warning-rule list and sort urgent items first."""
    results = []
    for rule in WARNING_RULES:
        value = facts.get(rule["metric"])
        if value is None:
            continue
        operator = rule["operator"]
        threshold = rule["threshold"]
        if operator == "false":
            fires = not bool(value)
        elif operator == "true":
            fires = bool(value)
        else:
            decimal_value = _decimal(value)
            fires = (
                decimal_value < threshold if operator == "lt" else
                decimal_value > threshold if operator == "gt" else
                decimal_value >= threshold if operator == "gte" else
                decimal_value == threshold if operator == "eq" else False
            )
        if fires:
            results.append({
                "id": rule["id"],
                "severity": rule["severity"],
                "icon": "!" if rule["severity"] == "Problem" else "?",
                "what": rule["what"],
                "why": rule["why"],
                "action": rule["action"],
            })
    order = {"Problem": 0, "Watch": 1, "Good": 2}
    return sorted(results, key=lambda row: (order[row["severity"]], row["id"]))


def _good_news(profile_metrics: Mapping[str, Any], plan: dict[str, Any] | None) -> list[str]:
    """List only positive facts that are present in the saved report data."""
    news = []
    emergency = profile_metrics.get("emergency_fund_months")
    if emergency is not None and _decimal(emergency) >= Decimal("3"):
        news.append(f"Your emergency fund covers {emergency} months.")
    savings_rate = profile_metrics.get("savings_rate")
    if savings_rate is not None and _decimal(savings_rate) >= Decimal("10"):
        news.append(f"Your savings rate is {savings_rate}%.")
    if plan and plan["parts"]:
        news.append(f"Your saved plan has {plan['part_count']} chosen parts.")
    return news or ["Keep adding updates to see your progress."]


def _format_rupees(value: object) -> str:
    """Format money with Indian digit grouping for report wording."""
    amount = _decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP)
    is_negative = amount < ZERO
    text = f"{abs(amount):.2f}"
    whole, paise = text.split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        leading = whole[:-3]
        groups = []
        while len(leading) > 2:
            groups.insert(0, leading[-2:])
            leading = leading[:-2]
        if leading:
            groups.insert(0, leading)
        whole = ",".join(groups + [last_three])
    return f"{'-' if is_negative else ''}₹{whole}.{paise}"


def _summary_text(
    past: ProgressSnapshot | None,
    present: ProgressSnapshot | None,
    profile_metrics: Mapping[str, Any],
    warnings: list[dict[str, Any]],
    good_news: list[str],
) -> list[str]:
    """Write four fixed, simple sentences using only the report's saved values."""
    if past is not None and past.health_score is not None:
        start_sentence = f"You started this period with a health score of {int(past.health_score)}."
    else:
        start_sentence = "We do not have an earlier health score for this period yet."
    if present is not None and present.health_score is not None:
        current_sentence = f"Your latest saved health score is {int(present.health_score)}."
    else:
        current_sentence = "Your profile is not complete enough to show a health score yet."
    positive = good_news[0] if good_news else "Keep adding updates to see your progress."
    positive_sentence = f"Good news: {positive}"
    next_step = warnings[0]["action"] if warnings else "Keep following your saved plan and review it every 6 months."
    fix_sentence = f"First, {next_step[0].lower() + next_step[1:]}"
    return [start_sentence, current_sentence, positive_sentence, fix_sentence]


def check_wording_numbers(text: str, report_data: Mapping[str, Any]) -> bool:
    """Check that every digit in fixed report wording appears in its data."""
    checked_data = {
        key: value for key, value in report_data.items()
        if key not in {"summary", "wording"}
    }
    serialized = json.dumps(_jsonable(checked_data), ensure_ascii=False)
    # Match ordinary decimals and comma-grouped amounts without joining version dots.
    numeric_pattern = r"\d+(?:,\d{3})*(?:\.\d+)?"
    available = {
        Decimal(number.replace(",", ""))
        for number in re.findall(numeric_pattern, serialized)
    }
    used = {
        Decimal(number.replace(",", ""))
        for number in re.findall(numeric_pattern, text)
    }
    return used.issubset(available)


def _warning_facts(
    metrics: Mapping[str, Any],
    plan_parts: list[dict[str, Any]],
    profile: Profile | None,
    goals: list[dict[str, Any]],
    market: dict[str, Any] | None,
    logs: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Calculate the named facts consumed by the shared warning rules."""
    debts = list(profile.debts or []) if profile is not None else []
    equity_share = sum(
        (_decimal(part["share"]) for part in plan_parts if "equity" in str(part["asset_class"]).lower()),
        ZERO,
    )
    locked_share = sum(
        (_decimal(part["share"]) for part in plan_parts if part["idea_id"] in {"ppf", "elss", "nps"}),
        ZERO,
    )
    goal_years = [int(goal["years_left"]) for goal in goals]
    recent = set()
    local_today = now.astimezone(INDIA).date()
    for offset in range(3):
        month_index = local_today.year * 12 + local_today.month - 1 - offset
        year, month_zero = divmod(month_index, 12)
        recent.add(f"{year:04d}-{month_zero + 1:02d}")
    positive_months = {
        row["month"] for row in logs["items"]
        if row["status"] != "Deleted" and _decimal(row["amount"]) > ZERO
    }
    missing_recent = sum(1 for month in recent if month not in positive_months) if goals else 0
    ahead_values = [
        _decimal(goal["ahead_behind_percent"])
        for goal in goals
        if goal.get("ahead_behind_percent") is not None
    ]
    chance_values = [
        _decimal(goal["chance_now"])
        for goal in goals
        if goal.get("chance_now") is not None
    ]
    analysis = metrics.get("plan_risk_ok")
    return {
        "emergency_fund_months": _decimal(metrics["emergency_fund_months"]) if metrics.get("emergency_fund_months") is not None else None,
        "max_interest_rate": max((_decimal(debt.get("interest_rate")) for debt in debts), default=None),
        "debt_to_income": _decimal(metrics["debt_to_income"]) if metrics.get("debt_to_income") is not None else None,
        "savings_rate": _decimal(metrics["savings_rate"]) if metrics.get("savings_rate") is not None else None,
        "plan_risk_ok": analysis,
        "short_goal_equity": bool(goal_years and min(goal_years) < 3 and equity_share > Decimal("30")),
        "locked_money": bool(goal_years and min(goal_years) < 5 and locked_share > Decimal("50")),
        "behind_percent": min(ahead_values) if ahead_values else None,
        "missed_recent_months": Decimal(missing_recent),
        "lowest_goal_chance": min(chance_values) if chance_values else None,
        "market_age_days": _market_age(market, now),
    }


def _status_for(value: Decimal | None, good: bool, caution: bool = False) -> dict[str, str]:
    """Give table rows a readable status word and icon alongside color."""
    if value is None:
        return {"label": "Not set", "icon": "—", "kind": "neutral"}
    if good:
        return {"label": "Good", "icon": "✓", "kind": "good"}
    if caution:
        return {"label": "Watch", "icon": "!", "kind": "watch"}
    return {"label": "Problem", "icon": "!", "kind": "problem"}


def _profile_section(
    profile: Profile | None,
    health_score: int | None,
) -> dict[str, Any]:
    """Build profile numbers, healthy ranges and the income comparison chart."""
    if profile is None or not profile.income:
        return {
            "metrics": {},
            "rows": [],
            "chart": {"labels": ["Income", "Expenses", "EMI", "Money left"], "values": ["0", "0", "0", "0"]},
            "empty": True,
        }
    income = _decimal(profile.income)
    expenses = _decimal(profile.expenses)
    savings = _decimal(profile.savings)
    debts = profile.debts or []
    emis = sum((_decimal(debt.get("emi")) for debt in debts), ZERO)
    money_left = calculate_money_left_after_debts(income, expenses, debts)
    savings_rate = calculate_savings_rate(income, expenses)
    dti = calculate_debt_to_income_ratio(emis, income)
    emergency = calculate_emergency_fund_months(savings, expenses)
    metrics = {
        "income": _money(income),
        "expenses": _money(expenses),
        "savings": _money(savings),
        "emi": _money(emis),
        "money_left": _money(money_left),
        "savings_rate": _number(savings_rate),
        "debt_to_income": _number(dti),
        "emergency_fund_months": _number(emergency),
        "health_score": health_score,
    }
    rows = [
        {"item": "Monthly income", "value": metrics["income"], "healthy_range": "Enough for expenses and EMI", "status": _status_for(income, money_left >= ZERO)},
        {"item": "Monthly expenses", "value": metrics["expenses"], "healthy_range": "Less than monthly income", "status": _status_for(expenses, expenses < income)},
        {"item": "Savings", "value": metrics["savings"], "healthy_range": "At least 3 months of expenses", "status": _status_for(savings, emergency >= Decimal("3"), emergency > ZERO)},
        {"item": "Money left each month", "value": metrics["money_left"], "healthy_range": "More than Rs 0", "status": _status_for(money_left, money_left > ZERO)},
        {"item": "Savings rate", "value": f'{metrics["savings_rate"]}%', "healthy_range": "10% or more", "status": _status_for(savings_rate, savings_rate >= Decimal("10"), savings_rate > ZERO)},
        {"item": "Debt-to-income", "value": f'{metrics["debt_to_income"]}%', "healthy_range": "40% or less", "status": _status_for(dti, dti <= Decimal("40"), dti <= Decimal("50"))},
        {"item": "Emergency fund months", "value": metrics["emergency_fund_months"], "healthy_range": "3 to 6 months", "status": _status_for(emergency, emergency >= Decimal("3"), emergency > ZERO)},
    ]
    return {
        "metrics": metrics,
        "rows": rows,
        "chart": {
            "labels": ["Income", "Expenses", "EMI", "Money left"],
            "values": [metrics["income"], metrics["expenses"], metrics["emi"], metrics["money_left"]],
        },
        "empty": False,
    }


def _plan_section(
    profile: Profile | None,
    plan: InvestmentPlan | None,
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create the chosen-parts table, score checks, risk meter and donut data."""
    parts = _saved_plan_parts(plan)
    monthly = _decimal(plan.monthly_amount) if plan is not None else ZERO
    share_total = sum((_decimal(part["share"]) for part in parts), ZERO)
    amount_total = sum((_decimal(part["monthly_amount"]) for part in parts), ZERO)
    checks = [
        {
            "name": check["name"],
            "status": str(check["status"]).title(),
            "score": int(check["score"]),
            "max_points": int(check["max_points"]),
            "message": str(check["message"]),
        }
        for check in (analysis or {}).get("checks", [])
    ]
    risk_value = _number(analysis.get("weighted_risk")) if analysis else None
    investor_type = profile.investor_type if profile is not None else None
    risk_ranges = {
        "conservative": ("1.0", "2.2"),
        "balanced": ("2.2", "3.5"),
        "aggressive": ("3.5", "5.0"),
    }
    risk_range = risk_ranges.get(str(investor_type or "").lower())
    return {
        "parts": parts,
        "part_count": len(parts),
        "monthly_amount": _money(monthly),
        "total_share": _number(share_total),
        "total_monthly": _money(amount_total),
        "plan_score": int(analysis["score"]) if analysis else None,
        "checks": checks,
        "risk": {
            "weighted": risk_value,
            "investor_type": investor_type,
            "range": list(risk_range) if risk_range else None,
            "within_range": (
                bool(analysis)
                and risk_range is not None
                and Decimal(risk_range[0]) <= _decimal(risk_value) <= Decimal(risk_range[1])
            ),
        },
        "donut": {
            "labels": [part["name"] for part in parts],
            "values": [part["share"] for part in parts],
        },
        "empty": not parts,
    }


def _journey(user: User) -> list[dict[str, Any]]:
    """Show the completion time for each setup step in the user's timeline."""
    steps = [
        ("Account", user.created_at),
        ("Money details", user.money_details_completed_at),
        ("Risk quiz", user.risk_quiz_completed_at),
        ("Investment choices", user.choices_completed_at),
        ("Plan review", user.plan_review_completed_at),
    ]
    return [
        {"step": label, "completed_at": _format_time(value), "complete": value is not None}
        for label, value in steps
    ]


def _actions(warnings: list[dict[str, Any]], goals: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    """Make a short, priority-ordered action list and a simple month checklist."""
    actions = [
        {
            "action": warning["action"],
            "why": warning["why"],
            "how_much": None,
            "by_when": "This week" if warning["severity"] == "Problem" else "This month",
        }
        for warning in warnings[:5]
    ]
    if not actions and goals:
        for goal in goals[:5]:
            actions.append({
                "action": goal["next_step"],
                "why": f"Keep your {goal['name']} goal moving.",
                "how_much": goal["catch_up_monthly"],
                "by_when": "This month",
            })
    elif not actions and plan["parts"]:
        actions.append({
            "action": "Review your saved plan every 6 months.",
            "why": "Your needs and market information can change.",
            "how_much": None,
            "by_when": "In 6 months",
        })
    actions = actions[:5]
    checklist = [
        {"task": action["action"], "done": False}
        for action in actions
    ]
    if not checklist:
        checklist = [{"task": "Add your money details and goals.", "done": False}]
    return {"items": actions, "checklist": checklist[:5]}


def build_report_data(user: User, db: Session, period: str = "since_started") -> dict[str, Any]:
    """Return every report section using only this signed-in user's saved data."""
    if period not in PERIOD_LABELS:
        raise HTTPException(status_code=422, detail="Choose a valid report period.")
    now = _now_utc()
    _ensure_monthly_snapshot(user, db, now)
    now = _now_utc()
    start = _period_start(user, period, now)
    snapshots = (
        db.query(ProgressSnapshot)
        .filter(
            ProgressSnapshot.user_id == user.id,
            ProgressSnapshot.created_at >= start,
            ProgressSnapshot.created_at <= now,
        )
        .order_by(ProgressSnapshot.created_at.asc(), ProgressSnapshot.id.asc())
        .all()
    )
    past = snapshots[0] if snapshots else None
    present = snapshots[-1] if snapshots else None
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user.id).first()
    from backend.goal_logs import ensure_goal_metadata

    saved_goals = ensure_goal_metadata(profile, user) if profile is not None else []
    if profile is not None and saved_goals != (profile.goals or []):
        db.commit()
    analysis = _plan_analysis(profile, plan)
    plan_section = _plan_section(profile, plan, analysis)
    health_score = None
    if profile is not None and profile.income:
        health_result = calculate_health_score(
            profile.income,
            profile.expenses or "0",
            profile.savings or "0",
            profile.debts or [],
            profile.goals or [],
        )
        health_score = int(health_result["score"])
    profile_section = _profile_section(profile, health_score)
    goals = _goal_report_rows(user, db, profile)
    current_value = sum((_decimal(goal["value_today"]) for goal in goals), ZERO)
    total_invested = sum((_decimal(goal["invested"]) for goal in goals), ZERO)
    monthly_amount = _decimal(plan.monthly_amount) if plan is not None else ZERO
    monthly_amount_suggestion = suggest_monthly_amount({
        "income": (profile.income if profile is not None else None) or "0",
        "expenses": (profile.expenses if profile is not None else None) or "0",
        "savings": (profile.savings if profile is not None else None) or "0",
        "debts": profile.debts if profile is not None else [],
        "goals": profile.goals if profile is not None else [],
        "income_stability": (
            profile.income_stability if profile is not None else "steady"
        ),
        "wanted_monthly_amount": (
            profile.wanted_monthly_amount if profile is not None else None
        ),
        "monthly_amount": plan.monthly_amount if plan is not None else None,
        "plan_parts": plan_section["parts"],
    })
    growth_profile = {
        "income": (profile.income if profile is not None else None) or "0",
        "expenses": (profile.expenses if profile is not None else None) or "0",
        "savings": (profile.savings if profile is not None else None) or "0",
        "debts": profile.debts if profile is not None else [],
        "goals": profile.goals if profile is not None else [],
        "investor_type": profile.investor_type if profile is not None else "balanced",
    }
    amount_for_outlook = (
        plan.monthly_amount
        if plan is not None
        else monthly_amount_suggestion["recommended"]
    )
    smart_amount_growth = calculate_amount_growth(
        amount_for_outlook,
        10,
        growth_profile,
        plan.parts if plan is not None else None,
        get_market_snapshot(),
    )
    today = now.astimezone(INDIA).date()
    debts = _debt_report(profile, today)
    logs = _investment_logs(user, db, monthly_amount, plan_section["parts"], today)
    market = _market_data()
    warning_context = _warning_facts(
        profile_section["metrics"],
        plan_section["parts"],
        profile,
        goals,
        market,
        logs,
        now,
    )
    warning_context["plan_risk_ok"] = plan_section["risk"]["within_range"] if plan_section["parts"] else None
    warnings = _warning_items(warning_context)
    good_news = _good_news(profile_section["metrics"], plan_section)
    outlook = _future_outlook(
        plan_section["parts"],
        monthly_amount,
        current_value,
        total_invested,
        goals,
    )
    comparison = _snapshot_comparison(past, present)
    snapshot_history = [
        {
            "date": _format_date(snapshot.created_at),
            "created_at": _format_time(snapshot.created_at),
            "health_score": _number(snapshot.health_score),
            "total_invested": _money(snapshot.total_invested),
            "value_today": _money(snapshot.value_today),
        }
        for snapshot in snapshots
    ]
    snapshot_has_data = any(
        snapshot.health_score is not None
        or snapshot.plan_score is not None
        or snapshot.monthly_income is not None
        or snapshot.total_invested not in (None, ZERO)
        or snapshot.value_today not in (None, ZERO)
        for snapshot in snapshots
    )
    journey = _journey(user)
    journey[-1]["investment_log_streak_months"] = max(
        (goal["streak_months"] for goal in goals),
        default=0,
    )
    journey[-1]["investment_log_consistency_percent"] = max(
        (goal["consistency_percent"] for goal in goals),
        default="0.00",
    )
    report_name = (user.email.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ").title() or "ArthMitra user")
    data: dict[str, Any] = {
        "app_credit": APP_CREDIT,
        "app_version": APP_VERSION,
        "name": report_name,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_at_local": _format_time(now),
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "period_start": _format_date(start),
        "period_end": _format_date(now),
        "summary": [],
        "key_cards": {
            "health_score": health_score,
            "plan_score": plan_section["plan_score"],
            "goal_chance": _number(min(
                (_decimal(goal["chance_now"]) for goal in goals),
                default=ZERO,
            )),
            "investor_type": profile.investor_type if profile is not None and profile.investor_type else "Not set",
        },
        "profile": profile_section,
        "monthly_amount_suggestion": monthly_amount_suggestion,
        "smart_amount_growth": smart_amount_growth,
        "journey": journey,
        "past_present": {
            "past_date": _format_date(past.created_at) if past else None,
            "present_date": _format_date(present.created_at) if present else None,
            "rows": comparison,
            "history": snapshot_history,
            "empty": not snapshot_has_data,
        },
        "plan": plan_section,
        "goals": goals,
        "debts": debts,
        "investment_logs": logs,
        "outlook": outlook,
        "warnings": {"items": warnings, "good_news": good_news},
        "actions": _actions(warnings, goals, plan_section),
        "market": market,
        "assumptions": {
            "rates": [
                {"idea": part["name"], "low": part["expected_return_low"], "middle": part["expected_return_mid"], "high": part["expected_return_high"]}
                for part in plan_section["parts"]
            ],
            "formula_notes": [
                "Monthly investment growth uses the annuity-due SIP formula.",
                "Each chosen plan part uses its own low, middle and high return assumption.",
                "Value snapshots are treated as actual values; other goal values are estimates.",
            ],
            "glossary": [
                {"term": "SIP", "meaning": "A set amount invested regularly."},
                {"term": "Compounding", "meaning": "Growth can also earn growth over time."},
                {"term": "Diversification", "meaning": "Spreading money across different kinds of investments."},
                {"term": "Inflation", "meaning": "Prices rising over time, so money buys less."},
                {"term": "Risk", "meaning": "The chance that an investment value can go up or down."},
                {"term": "Liquidity", "meaning": "How easily you can take money out."},
                {"term": "DTI", "meaning": "Monthly debt payments divided by monthly income."},
            ],
            "disclaimer": DISCLAIMER,
        },
        "disclaimer": DISCLAIMER,
        "report_ready": {
            "has_profile": bool(profile and profile.income),
            "has_plan": not plan_section["empty"],
            "has_goals": bool(goals),
            "has_logs": not logs["empty"],
            "has_debts": not debts["empty"],
        },
    }
    data["summary"] = _summary_text(past, present, profile_section["metrics"], warnings, good_news)
    if not check_wording_numbers(" ".join(data["summary"]), data):
        data["summary"] = [
            "Your report is ready.",
            "The numbers below come from your saved information.",
            "Keep adding updates to see your progress.",
            "Review your plan before making a change.",
        ]
    return _jsonable(data)


def _pdf_allowed(user: User) -> bool:
    """Limit each signed-in user to five PDF files in one minute."""
    now = time.monotonic()
    attempts = PDF_ATTEMPTS.setdefault(user.id, deque())
    while attempts and now - attempts[0] > PDF_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= PDF_LIMIT:
        return False
    attempts.append(now)
    return True


def _chart_image(kind: str, report: Mapping[str, Any]) -> io.BytesIO | None:
    """Draw one report chart on the server so it also appears in the PDF."""
    figure, axis = plt.subplots(figsize=(7, 3.2), dpi=120)
    figure.patch.set_facecolor("#ffffff")
    axis.set_facecolor("#ffffff")
    if kind == "profile":
        if report["profile"]["empty"]:
            plt.close(figure)
            return None
        chart = report["profile"]["chart"]
        axis.bar(chart["labels"], [float(value) for value in chart["values"]], color="#3977d5")
        axis.set_ylabel("Rupees per month")
    elif kind == "health":
        history = report["past_present"]["history"]
        history = [row for row in history if row["health_score"] is not None]
        if not history:
            plt.close(figure)
            return None
        axis.plot([row["date"] for row in history], [float(row["health_score"] or 0) for row in history], color="#287a5b", marker="o")
        axis.set_ylabel("Health score")
    elif kind == "invested":
        history = report["past_present"]["history"]
        if report["past_present"]["empty"] or not history:
            plt.close(figure)
            return None
        axis.plot([row["date"] for row in history], [float(row["total_invested"]) for row in history], label="Invested", color="#3977d5")
        axis.plot([row["date"] for row in history], [float(row["value_today"]) for row in history], label="Value today", color="#ef8c31")
        axis.legend()
        axis.set_ylabel("Rupees")
    elif kind == "logs":
        if report["investment_logs"]["empty"]:
            plt.close(figure)
            return None
        chart = report["investment_logs"]["chart"]
        axis.bar(chart["labels"], [float(value) for value in chart["planned"]], label="Planned", color="#9ab7eb")
        axis.bar(chart["labels"], [float(value) for value in chart["actual"]], label="Actual", color="#3977d5", alpha=0.8)
        axis.legend()
        axis.set_ylabel("Rupees")
    elif kind == "plan":
        donut = report["plan"]["donut"]
        if not donut["values"]:
            plt.close(figure)
            return None
        axis.pie([float(value) for value in donut["values"]], labels=donut["labels"], autopct="%1.0f%%", startangle=90)
        axis.axis("equal")
    elif kind == "goals":
        goals = report["goals"]
        if not goals:
            plt.close(figure)
            return None
        for goal in goals:
            chart = goal["chart"]
            axis.plot(chart["labels"], [float(value) for value in chart["planned"]], linestyle="--", label=f'{goal["name"]} planned')
            axis.plot(chart["labels"], [float(value) for value in chart["actual"]], label=f'{goal["name"]} actual')
        axis.set_ylabel("Cumulative rupees")
        axis.legend(fontsize=7)
    elif kind == "debts":
        chart = report["debts"]["chart"]
        if not chart["labels"]:
            plt.close(figure)
            return None
        axis.plot(chart["labels"], [float(value) for value in chart["balance"]], color="#c34a4a")
        axis.set_ylabel("Remaining rupees")
    elif kind == "future":
        curve = report["outlook"]["curve"]
        axis.plot(curve["years"], [float(value) for value in curve["follow_plan"]], label="Follow plan")
        axis.plot(curve["years"], [float(value) for value in curve["invested_so_far"]], label="Invest only what you invested")
        axis.plot(curve["years"], [float(value) for value in curve["stop_investing"]], label="Stop investing")
        if curve["goal_target"] is not None:
            axis.axhline(float(curve["goal_target"]), label=f'{curve["goal_name"]} goal', color="#64748b", linestyle=":")
        axis.set_ylabel("Rupees")
        axis.legend(fontsize=7)
    axis.grid(axis="y", alpha=0.2)
    if kind in {"profile", "invested", "logs", "goals", "debts", "future"}:
        axis.yaxis.set_major_formatter(FuncFormatter(_chart_money_label))
    axis.tick_params(axis="x", labelrotation=25, labelsize=7)
    figure.tight_layout()
    output = io.BytesIO()
    figure.savefig(output, format="png", bbox_inches="tight")
    plt.close(figure)
    output.seek(0)
    return output


def _pdf_table(rows: list[list[Any]], widths: list[float] | None = None) -> Table:
    """Make a readable light-theme PDF table with repeating header rows."""
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "ArthMitraSans"),
        ("FONTNAME", (0, 0), (-1, 0), "ArthMitraSans-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf1fb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172033")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cad5e4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _register_pdf_fonts() -> None:
    """Load a Unicode font so Indian rupees and simple symbols print correctly."""
    global PDF_FONTS_READY
    if PDF_FONTS_READY:
        return
    font_sets = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ),
    ]
    selected = next(
        (
            (regular, bold)
            for regular, bold in font_sets
            if regular.is_file() and bold.is_file()
        ),
        None,
    )
    if selected is None:
        raise RuntimeError("A Unicode font is needed to create an Indian-rupee PDF.")
    regular, bold = selected
    pdfmetrics.registerFont(TTFont("ArthMitraSans", str(regular)))
    pdfmetrics.registerFont(TTFont("ArthMitraSans-Bold", str(bold)))
    registerFontFamily(
        "ArthMitraSans",
        normal="ArthMitraSans",
        bold="ArthMitraSans-Bold",
        italic="ArthMitraSans",
        boldItalic="ArthMitraSans-Bold",
    )
    PDF_FONTS_READY = True


def _pdf_value(value: object) -> str:
    """Turn missing values into a friendly dash before writing the PDF."""
    return "—" if value is None else str(value)


def _pdf_money(value: object) -> str:
    """Show PDF money in Indian rupee grouping, including lakh and crore groups."""
    return "—" if value is None else _format_rupees(value)


def _chart_money_label(value: float, _position: int) -> str:
    """Format a chart's rupee axis with Indian digit grouping."""
    return _format_rupees(value)


def _pdf_document(report: dict[str, Any]) -> bytes:
    """Create a real A4 PDF with all report sections, tables, charts and footer."""
    _register_pdf_fonts()
    styles = getSampleStyleSheet()
    for style_name in ("Normal", "BodyText", "Title", "Heading1", "Heading2"):
        styles[style_name].fontName = "ArthMitraSans"
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="ArthMitraSans-Bold", alignment=TA_CENTER, textColor=colors.HexColor("#174a8b"), spaceAfter=8))
    styles.add(ParagraphStyle(name="ReportSection", parent=styles["Heading1"], fontName="ArthMitraSans-Bold", textColor=colors.HexColor("#174a8b"), spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="ReportSub", parent=styles["Heading2"], fontName="ArthMitraSans-Bold", textColor=colors.HexColor("#334155"), spaceBefore=6, spaceAfter=3))
    styles.add(ParagraphStyle(name="ReportBody", parent=styles["BodyText"], fontName="ArthMitraSans", fontSize=9, leading=12))
    output = io.BytesIO()
    document = BaseDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=22 * mm, bottomMargin=20 * mm)
    frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="report-frame")
    def draw_page(canvas: Any, doc: Any) -> None:
        """Draw the report name, page number, developer credit and disclaimer on each page."""
        canvas.saveState()
        canvas.setFont("ArthMitraSans-Bold", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(16 * mm, A4[1] - 13 * mm, f'{report["name"]}  |  {report["generated_at_local"]}')
        canvas.setFont("ArthMitraSans", 7)
        canvas.drawCentredString(A4[0] / 2, 15 * mm, APP_CREDIT)
        canvas.drawCentredString(A4[0] / 2, 9 * mm, DISCLAIMER)
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()
    document.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=draw_page)])
    story: list[Any] = []
    def add_pdf_section(title: str, meaning: str, note: str) -> None:
        """Start one PDF section with the same two-line meaning box as the page."""
        story.append(Paragraph(title, styles["ReportSection"]))
        story.append(_pdf_table([
            ["What this means", "Good news / Watch out"],
            [
                Paragraph(meaning, styles["ReportBody"]),
                Paragraph(note, styles["ReportBody"]),
            ],
        ]))

    story.append(Paragraph("ArthMitra Money Report", styles["ReportTitle"]))
    story.append(Paragraph(f'{report["name"]} · Generated {report["generated_at_local"]} · {report["period_label"]}', styles["ReportBody"]))
    story.append(Spacer(1, 5 * mm))
    add_pdf_section(
        "1. COVER AND SUMMARY",
        "This is a simple view of your saved money details and progress.",
        "Good news: your report is ready. Watch out for any Problem items below.",
    )
    cards = report["key_cards"]
    story.append(_pdf_table([
        ["Health score", "Plan score", "Goal chance", "Investor type"],
        [_pdf_value(cards["health_score"]), _pdf_value(cards["plan_score"]), f'{cards["goal_chance"]}%' if cards["goal_chance"] is not None else "—", str(cards["investor_type"])],
    ]))
    for sentence in report["summary"]:
        story.append(Paragraph(sentence, styles["ReportBody"]))
    sections = [
        "2. YOUR PROFILE TODAY",
        "3. YOUR JOURNEY SO FAR",
        "4. PAST VS PRESENT",
        "5. YOUR INVESTMENT PLAN",
        "6. GOALS",
        "7. DEBTS",
        "8. INVESTMENT LOG",
        "9. FUTURE OUTLOOK",
        "10. WARNINGS AND ALERTS",
        "11. ACTION PLAN",
        "12. MARKET SNAPSHOT",
        "13. HOW WE CALCULATED",
    ]
    add_pdf_section(sections[0], "This shows your income, spending, savings and monthly debt payments.", "Check any row marked Watch or Problem.")
    profile_rows = [["Item", "Value", "Healthy range", "Status"]]
    for row in report["profile"]["rows"]:
        profile_value = (
            row["value"]
            if row["item"] in {"Savings rate", "Debt-to-income", "Emergency fund months"}
            else _pdf_money(row["value"])
        )
        profile_rows.append([row["item"], profile_value, row["healthy_range"], f'{row["status"]["icon"]} {row["status"]["label"]}'])
    if len(profile_rows) == 1:
        profile_rows.append(["Profile", "No money details saved yet", "Add your profile", "Watch"])
    story.append(_pdf_table(profile_rows, [42 * mm, 32 * mm, 58 * mm, 30 * mm]))
    monthly_suggestion = report["monthly_amount_suggestion"]
    story.append(Paragraph("Smart monthly amount", styles["ReportSub"]))
    story.append(_pdf_table([
        ["Comfortable", "Recommended", "Stretch"],
        [
            _pdf_money(monthly_suggestion["comfortable"]),
            _pdf_money(monthly_suggestion["recommended"]),
            _pdf_money(monthly_suggestion["stretch"]),
        ],
        ["You want", "You can", "Your goal needs"],
        [
            _pdf_money(monthly_suggestion["wanted"]),
            _pdf_money(monthly_suggestion["can"]),
            _pdf_money(monthly_suggestion["goal_need"])
            if monthly_suggestion["goal_need"] is not None
            else "Add a goal",
        ],
    ], [53 * mm, 53 * mm, 53 * mm]))
    story.append(Paragraph(
        str(monthly_suggestion["plain_english"]),
        styles["ReportBody"],
    ))
    chart = _chart_image("profile", report)
    if chart:
        story.append(Image(chart, width=160 * mm, height=72 * mm))
    add_pdf_section(sections[1], "This shows when you completed each setup step.", "Keep adding monthly investment updates.")
    story.append(_pdf_table(
        [["Setup step", "Completed at (Asia/Kolkata)"]]
        + [[step["step"], step["completed_at"] or "Not completed yet"] for step in report["journey"]]
        + [["Investment streak", f'{report["journey"][-1].get("investment_log_streak_months", 0)} months']]
        + [["Log consistency", f'{report["journey"][-1].get("investment_log_consistency_percent", "0.00")}%']],
    ))
    add_pdf_section(sections[2], "This compares your first and latest saved report snapshots.", "A new value means there was no earlier value to compare.")
    comparison_rows = [["Item", "Past", "Present", "Change", "Change %", "Arrow"]]
    for row in report["past_present"]["rows"]:
        non_money = row["item"] in {"Health score", "Plan score", "Emergency fund months"} or row["item"].startswith("Goal chance:")
        comparison_rows.append([
            row["item"],
            _pdf_money(row["past"]) if not non_money else _pdf_value(row["past"]),
            _pdf_money(row["present"]) if not non_money else _pdf_value(row["present"]),
            _pdf_money(row["change"]) if not non_money else _pdf_value(row["change"]),
            _pdf_value(row["change_percent"]),
            row["arrow"],
        ])
    if report["past_present"]["empty"]:
        story.append(Paragraph(
            "Past and present comparisons will appear after your first saved profile or plan update.",
            styles["ReportBody"],
        ))
    else:
        story.append(_pdf_table(comparison_rows))
        for kind in ("health", "invested"):
            chart = _chart_image(kind, report)
            if chart:
                story.append(Image(chart, width=160 * mm, height=72 * mm))
    add_pdf_section(sections[3], "This table shows only investments in your saved plan.", "Expected growth is an assumption, not a promise.")
    plan_rows = [["Idea", "Share %", "Each month", "Risk", "Expected range"]]
    for part in report["plan"]["parts"]:
        plan_rows.append([
            part["name"], part["share"], _pdf_money(part["monthly_amount"]), part["risk_words"],
            f'{part["expected_return_low"]}%–{part["expected_return_high"]}%',
        ])
    plan_rows.append(["Total", report["plan"]["total_share"], _pdf_money(report["plan"]["total_monthly"]), "", ""])
    if len(plan_rows) == 2:
        plan_rows = [["Idea", "Share %", "Each month", "Risk", "Expected range"], ["No saved plan", "—", "—", "—", "—"]]
    story.append(_pdf_table(plan_rows, [42 * mm, 20 * mm, 30 * mm, 34 * mm, 36 * mm]))
    if report["plan"]["plan_score"] is not None:
        story.append(Paragraph(f'Plan score: {report["plan"]["plan_score"]} / 100 · Risk score: {_pdf_value(report["plan"]["risk"]["weighted"])}', styles["ReportBody"]))
        risk_width = document.width * max(
            1,
            min(99, float(report["plan"]["risk"]["weighted"] or 0) * 20),
        ) / 100
        risk_meter = Table(
            [["", ""]],
            colWidths=[risk_width, document.width - risk_width],
            rowHeights=[7],
        )
        risk_meter.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#3977d5")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e2e8f0")),
        ]))
        story.append(risk_meter)
        story.append(_pdf_table([["Plan check", "Status", "Score", "What it says"]] + [
            [row["name"], row["status"], f'{row["score"]}/{row["max_points"]}', row["message"]]
            for row in report["plan"]["checks"]
        ]))
    chart = _chart_image("plan", report)
    if chart:
        story.append(Image(chart, width=125 * mm, height=70 * mm))
    add_pdf_section(sections[4], "Goal progress uses your real logged amounts and clearly named estimates.", "Keep logging what you really invest.")
    goal_rows = [["Goal", "Target", "Years left", "Invested", "Value today", "Planned by now", "Ahead/behind", "Chance", "Catch-up/month"]]
    for goal in report["goals"]:
        goal_rows.append([
            goal["name"], _pdf_money(goal["target"]), goal["years_left"], _pdf_money(goal["invested"]),
            f'{_pdf_money(goal["value_today"])} ({goal["value_label"]})', _pdf_money(goal["planned_by_now"]),
            _pdf_money(goal["ahead_behind"]), f'{goal["chance_now"]}%', _pdf_money(goal["catch_up_monthly"]),
        ])
    if len(goal_rows) == 1:
        goal_rows.append(["No goals saved yet", "—", "—", "—", "—", "—", "—", "—", "—"])
    story.append(_pdf_table(goal_rows))
    chart = _chart_image("goals", report)
    if chart:
        story.append(Image(chart, width=160 * mm, height=72 * mm))
    add_pdf_section(sections[5], "This compares two ways to pay your saved debts.", "Check the interest and estimated payoff date.")
    debt_rows = [["Debt", "Balance", "Rate", "EMI", "Months left", "Interest left"]]
    for debt in report["debts"]["items"]:
        debt_rows.append([
            debt["name"], _pdf_money(debt["balance"]), f'{debt["interest_rate"]}%', _pdf_money(debt["emi"]),
            _pdf_value(debt["months_left"]), _pdf_money(debt["interest_left"]),
        ])
    if len(debt_rows) == 1:
        debt_rows.append(["No debts saved", "—", "—", "—", "—", "—"])
    story.append(_pdf_table(debt_rows))
    story.append(Paragraph(f'Avalanche: {_pdf_money(report["debts"]["avalanche"]["interest"])} interest · {_pdf_value(report["debts"]["avalanche"]["debt_free_date"])} debt-free. Snowball: {_pdf_money(report["debts"]["snowball"]["interest"])} interest · {_pdf_value(report["debts"]["snowball"]["debt_free_date"])} debt-free.', styles["ReportBody"]))
    chart = _chart_image("debts", report)
    if chart:
        story.append(Image(chart, width=160 * mm, height=72 * mm))
    add_pdf_section(sections[6], "This lists your monthly investment updates.", "Deleted entries stay in history but are not counted in totals.")
    log_rows = [["Date and time", "Month", "Amount", "Part", "Note", "Status"]]
    for row in report["investment_logs"]["items"]:
        log_rows.append([_pdf_value(row["date_time"]), row["month"], _pdf_money(row["amount"]), _pdf_value(row["part"]), _pdf_value(row["note"]), row["status"]])
    if len(log_rows) == 1:
        log_rows.append(["No investment updates yet", "—", "—", "—", "—", "—"])
    story.append(_pdf_table(log_rows))
    story.append(Paragraph(f'Planned in the last 12 months: {_pdf_money(report["investment_logs"]["planned_last_12_months"])}. Actual: {_pdf_money(report["investment_logs"]["actual_last_12_months"])}.', styles["ReportBody"]))
    chart = _chart_image("logs", report)
    if chart:
        story.append(Image(chart, width=160 * mm, height=72 * mm))
    add_pdf_section(sections[7], "These are possible results from the saved plan's separate parts.", "These are assumptions, not predictions or guarantees.")
    if report["outlook"]["empty"]:
        story.append(Paragraph("Save a plan to see possible future outcomes.", styles["ReportBody"]))
    else:
        outlook_rows = [["Years", "Low (value / earned)", "Middle (value / earned)", "High (value / earned)", "Total invested"]]
        for row in report["outlook"]["rows"]:
            outlook_rows.append([
                row["years"],
                f'{_pdf_money(row["low"]["value"])} / {_pdf_money(row["low"]["earned"])}',
                f'{_pdf_money(row["mid"]["value"])} / {_pdf_money(row["mid"]["earned"])}',
                f'{_pdf_money(row["high"]["value"])} / {_pdf_money(row["high"]["earned"])}',
                _pdf_money(row["mid"]["invested"]),
            ])
        story.append(_pdf_table(outlook_rows))
        chart = _chart_image("future", report)
        if chart:
            story.append(Image(chart, width=160 * mm, height=72 * mm))
        story.append(Paragraph(
            f'In one bad year your plan could temporarily fall by about {report["outlook"]["stress_test"]["fall_percent"]}% (about {_pdf_money(report["outlook"]["stress_test"]["loss"])}).',
            styles["ReportBody"],
        ))
        forecast_rows = [["Goal", "Low chance / year", "Middle chance / year", "High chance / year"]]
        for row in report["outlook"]["goal_forecasts"]:
            forecast_rows.append([
                row["goal"],
                f'{row["low"]["chance_percent"]}% / {_pdf_value(row["low"]["year_reached"])}',
                f'{row["mid"]["chance_percent"]}% / {_pdf_value(row["mid"]["year_reached"])}',
                f'{row["high"]["chance_percent"]}% / {_pdf_value(row["high"]["year_reached"])}',
            ])
        if len(forecast_rows) > 1:
            story.append(_pdf_table(forecast_rows))
    smart_growth = report["smart_amount_growth"]
    story.append(Paragraph("Smart monthly amount · 10-year outlook", styles["ReportSub"]))
    if smart_growth["mode"] == "growth":
        story.append(_pdf_table([
            ["Monthly amount", "Invested", "Low", "Middle", "High"],
            [
                _pdf_money(smart_growth["amount"]),
                _pdf_money(smart_growth["totals"]["invested"]),
                _pdf_money(smart_growth["totals"]["low"]),
                _pdf_money(smart_growth["totals"]["mid"]),
                _pdf_money(smart_growth["totals"]["high"]),
            ],
        ]))
    else:
        story.append(Paragraph(str(smart_growth["message"]), styles["ReportBody"]))
    story.append(Paragraph(
        "Expected, not guaranteed. These are possible outcomes, not promises.",
        styles["ReportBody"],
    ))
    add_pdf_section(sections[8], "These checks point out things you may want to review.", "Start with any Problem item.")
    warning_rows = [["Severity", "What we noticed", "Why it matters", "What to do"]]
    warning_rows.extend([[f'{row["icon"]} {row["severity"]}', row["what"], row["why"], row["action"]] for row in report["warnings"]["items"]])
    if len(warning_rows) == 1:
        warning_rows.append(["✓ Good", "No warning matched your saved information.", "Keep checking your plan.", "Review your plan every 6 months."])
    story.append(_pdf_table(warning_rows))
    story.append(Paragraph("Good news", styles["ReportSub"]))
    for item in report["warnings"]["good_news"]:
        story.append(Paragraph(f"• {item}", styles["ReportBody"]))
    add_pdf_section(sections[9], "This is a short list of useful next steps.", "Tick off each step as you complete it.")
    action_rows = [["Action", "Why", "How much", "By when"]]
    action_rows.extend([[row["action"], row["why"], _pdf_money(row["how_much"]), row["by_when"]] for row in report["actions"]["items"]])
    if len(action_rows) == 1:
        action_rows.append(["No action yet", "Add your details to get a helpful next step.", "—", "—"])
    story.append(_pdf_table(action_rows))
    story.append(Paragraph("Next 30 days", styles["ReportSub"]))
    story.append(_pdf_table([["Done", "Checklist"]] + [["☐", item["task"]] for item in report["actions"]["checklist"]]))
    add_pdf_section(sections[10], "These public figures include their source and saved date.", "Market information may be old or may change.")
    if report["market"] and report["market"]["items"]:
        story.append(Paragraph(f'Data as of {report["market"]["data_as_of"]}. {report["market"]["message"]}', styles["ReportBody"]))
        story.append(_pdf_table([["Market number", "Value", "Source"]]
            + [[row["name"], row["value"], row["source_url"]] for row in report["market"]["items"]]))
    else:
        story.append(Paragraph("No market snapshot is available right now.", styles["ReportBody"]))
    add_pdf_section(sections[11], "This explains the assumptions and money terms used in the report.", "Use the report for learning, not as a promise of profit.")
    for note in report["assumptions"]["formula_notes"]:
        story.append(Paragraph(f"• {note}", styles["ReportBody"]))
    story.append(Paragraph("Assumed return rates", styles["ReportSub"]))
    story.append(_pdf_table([["Idea", "Low", "Middle", "High"]] + [
        [row["idea"], f'{row["low"]}%', f'{row["middle"]}%', f'{row["high"]}%']
        for row in report["assumptions"]["rates"]
    ] if report["assumptions"]["rates"] else [["Idea", "Low", "Middle", "High"], ["No saved plan", "—", "—", "—"]]))
    story.append(Paragraph("Glossary", styles["ReportSub"]))
    story.append(_pdf_table([["Word", "Meaning"]] + [[row["term"], row["meaning"]] for row in report["assumptions"]["glossary"]]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(DISCLAIMER, styles["ReportBody"]))
    document.build(story)
    return output.getvalue()


@router.get("/report/data")
def get_report_data(
    period: str = Query(default="since_started"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Return one complete private report and prevent browser or proxy caching."""
    data = build_report_data(user, db, period)
    return Response(
        content=json.dumps(data, ensure_ascii=False),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/report/pdf")
def get_report_pdf(
    period: str = Query(default="since_started"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Create a rate-limited PDF from the same owner-only report data."""
    if not _pdf_allowed(user):
        raise HTTPException(status_code=429, detail="Too many PDF downloads. Please wait a minute and try again.")
    data = build_report_data(user, db, period)
    pdf_bytes = _pdf_document(data)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", data["name"]).strip("_") or "User"
    local_date = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00")).astimezone(INDIA).strftime("%Y-%m-%d")
    filename = f"ArthMitra_Report_{safe_name}_{local_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/report/csv")
def get_report_csv(
    period: str = Query(default="since_started"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download a spreadsheet of profile, plan, goal, debt and log values."""
    report = build_report_data(user, db, period)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Item", "Value"])
    for row in report["profile"]["rows"]:
        writer.writerow(["Profile", row["item"], row["value"]])
    for part in report["plan"]["parts"]:
        writer.writerow(["Plan", part["name"], part["monthly_amount"]])
    for goal in report["goals"]:
        writer.writerow(["Goal", goal["name"], goal["value_today"]])
    for debt in report["debts"]["items"]:
        writer.writerow(["Debt", debt["name"], debt["balance"]])
    for log in report["investment_logs"]["items"]:
        writer.writerow(["Investment log", log["month"], log["amount"]])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="ArthMitra_Report_data.csv"',
        },
    )
