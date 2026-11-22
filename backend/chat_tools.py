"""Provide trusted idea and allocation tools for the built-in coach."""

from decimal import Decimal
from typing import Any, Mapping

from backend.analysis import analyze_plan as run_plan_analysis
from backend.calculators import allocation_plan, suggest_monthly_amount as calculate_monthly_amount
from backend.investment_ideas import ideas_for_user
from backend.market_data import get_market_snapshot, market_summary
from backend.suggest import build_smart_suggestion
from backend.smart_amount import calculate_amount_growth


def analyze_plan(user: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    """Return real plan scores and goal estimates for the coach to explain."""
    return run_plan_analysis(user, plan)


def suggest_fix(user: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the highest-impact fixes from the saved plan analysis."""
    return analyze_plan(user, plan)["top_fixes"]


def get_onboarding_status(user: Mapping[str, Any]) -> dict[str, Any]:
    """Describe the next setup screen using the saved onboarding step."""
    pages = {
        0: ("money-details", 2),
        1: ("retake-quiz", 3),
        2: ("investment-choices", 4),
        3: ("plan-review", 5),
        4: ("dashboard", 5),
    }
    step = min(max(int(user.get("onboarding_step", 0)), 0), 4)
    next_page, step_number = pages[step]
    return {
        "onboarding_step": step,
        "next_page": next_page,
        "step_number": step_number,
        "complete": step == 4,
    }


def get_investment_ideas(user: Mapping[str, Any]) -> dict[str, Any]:
    """Return real, sorted idea matches for the coach to explain."""
    ideas = ideas_for_user(user)
    return {
        "ideas": ideas,
        "top_picks": [idea for idea in ideas if not idea["locked"]][:3],
    }


def get_allocation_plan(monthly_amount: object, user: Mapping[str, Any]) -> dict[str, Any]:
    """Return a real monthly split or the basics that need fixing first."""
    if not bool(user.get("ready")):
        steps = []
        if not user.get("no_monthly_expenses") and user.get("emergency_fund_months", 0) < 3:
            steps.append("Build an emergency fund for at least 3 months of expenses.")
        if user.get("has_high_interest_debt"):
            steps.append("Pay down debt above 15% interest before investing in higher-risk ideas.")
        if not steps:
            steps.append("Add your income, expenses and savings before making an investment plan.")
        return {"ready": False, "items": [], "fix_plan": steps}
    return {"ready": True, **allocation_plan(monthly_amount, str(user["investor_type"]))}


def get_market_snapshot_tool(refresh: bool = False) -> dict[str, Any]:
    """Return checked market figures, dates, source links and any stale-data note."""
    snapshot = get_market_snapshot(refresh=refresh)
    return {
        **snapshot,
        "summary": market_summary(snapshot),
    }


def get_goal_progress(progress: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Turn calculated goal progress into a short, honest coach answer."""
    if not progress:
        return {
            "answer": "Add a goal and log your monthly investments so I can check your progress.",
            "goals": [],
        }
    summaries = []
    for item in progress:
        goal = item["goal"]
        difference = item["ahead_behind"]
        direction = "ahead" if Decimal(str(difference)) >= 0 else "behind"
        amount = abs(Decimal(str(difference)))
        summaries.append({
            "goal": goal["name"],
            "direction": direction,
            "amount": str(amount),
            "value_today": str(item["value_today"]),
            "chance": str(item["chance_with_real_investments"]),
            "catch_up_monthly": (
                str(item["catch_up_monthly"])
                if item["catch_up_monthly"] is not None
                else None
            ),
        })
    first = summaries[0]
    answer = (
        f"For {first['goal']}, you are {first['direction']} your plan by "
        f"Rs {first['amount']}. Your current estimated goal chance is "
        f"{first['chance']}%."
    )
    if first["catch_up_monthly"] is not None:
        answer += f" To stay on track, invest about Rs {first['catch_up_monthly']} per month."
    return {"answer": answer, "goals": summaries}


def suggest_monthly_amount(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Give the coach the same Decimal amount suggestion shown in the app."""
    return calculate_monthly_amount(profile)


def get_amount_growth(
    amount: object,
    years: int,
    profile: Mapping[str, Any],
    saved_parts: list[Mapping[str, Any]] | None,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a backend-calculated growth answer for one monthly amount."""
    projection = calculate_amount_growth(
        amount,
        years,
        profile,
        saved_parts,
        snapshot,
    )
    if projection["mode"] == "growth":
        totals = projection["totals"]
        answer = (
            f"If you invest Rs {Decimal(str(projection['amount'])):,.2f} each month "
            f"for {years} years, you could have about "
            f"Rs {Decimal(str(totals['mid'])):,.2f} (middle case). "
            f"You put in Rs {Decimal(str(totals['invested'])):,.2f}."
        )
    else:
        answer = projection["message"]
    return {"answer": answer, "projection": projection}


def explain_plan_choice(
    user: Mapping[str, Any],
    plan: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Explain a plan's actual part count and choices with sourced market data."""
    readiness = user.get("readiness") or {
        "ready": bool(user.get("ready", False)),
        "emergency_fund_months": user.get("emergency_fund_months", "0"),
        "has_high_interest_debt": bool(user.get("has_high_interest_debt", False)),
    }
    suggestion = build_smart_suggestion(
        plan.get("monthly_amount", user.get("monthly_amount", "0")),
        str(user.get("investor_type", "balanced")),
        list(user.get("goals") or []),
        readiness,
        snapshot,
        bool(plan.get("tax_saving_80c", False)),
    )
    saved_parts = list(plan.get("parts") or [])
    return {
        "part_count": len(saved_parts),
        "suggested_part_count": suggestion["part_count"],
        "part_count_reason": suggestion["why_this_plan"]["part_count_reason"],
        "market_summary": suggestion["why_this_plan"]["market_summary"],
        "data_as_of": suggestion["why_this_plan"]["data_as_of"],
        "sources": suggestion["why_this_plan"]["sources"],
        "changes_from_standard_mix": suggestion["tilts"],
        "risk_band_exception": suggestion["risk_band_exception"],
        "label": "Assumptions, not guarantees.",
    }
