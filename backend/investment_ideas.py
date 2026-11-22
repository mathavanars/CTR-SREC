"""Load the one investment-idea catalog and match ideas to a person's details."""

import json
from pathlib import Path
from decimal import Decimal
from typing import Any, Mapping


IDEAS_PATH = Path(__file__).resolve().parent / "data" / "investment_ideas.json"
REQUIRED_IDEA_FIELDS = {
    "id", "name", "asset_class", "school_explanation", "real_life_example",
    "risk_level", "risk_words", "expected_return_low", "expected_return_mid",
    "expected_return_high", "minimum_to_start", "time_needed", "money_access",
    "good_for", "pros", "cons", "how_to_start", "quiz", "last_checked",
}


def load_investment_ideas() -> list[dict[str, Any]]:
    """Read all idea facts from the shared JSON catalog."""
    with IDEAS_PATH.open(encoding="utf-8") as ideas_file:
        catalog = json.load(ideas_file)
    return catalog["ideas"]


def load_basics_jars() -> list[dict[str, Any]]:
    """Read emergency-fund and debt-payoff choices from the shared catalog."""
    with IDEAS_PATH.open(encoding="utf-8") as ideas_file:
        catalog = json.load(ideas_file)
    return catalog["special_jars"]


def match_score(idea: Mapping[str, Any], user: Mapping[str, Any]) -> dict[str, Any]:
    """Score one idea for the user and mark risky ideas locked when basics are not ready."""
    score = 50
    investor_type = str(user.get("investor_type") or "balanced").lower()
    reasons = []
    if investor_type in idea["good_for"]:
        score += 30
        reasons.append(f"Fits your {investor_type.title()} style.")
    else:
        score -= 20
        reasons.append(f"May not fit your {investor_type.title()} style.")

    goals = user.get("goals") or []
    nearest_goal_years = min((int(goal["years"]) for goal in goals), default=None)
    if nearest_goal_years is not None and nearest_goal_years < 3 and idea["risk_level"] >= 4:
        score -= 30
        reasons.append("Your nearest goal is soon, so this higher-risk idea is a weaker fit.")
    elif nearest_goal_years is not None:
        reasons.append(f"Your nearest goal is {nearest_goal_years} years away.")

    emergency_months = Decimal(str(user.get("emergency_fund_months") or 0))
    has_high_interest_debt = bool(user.get("has_high_interest_debt"))
    locked = (
        not bool(user.get("ready", False))
        and (emergency_months < 3 or has_high_interest_debt)
        and idea["risk_level"] >= 3
    )
    lock_reason = (
        "Fix basics first. Build your emergency fund and clear high-interest debt, then this unlocks."
        if locked
        else None
    )

    monthly_amount = Decimal(str(user.get("monthly_amount") or 0))
    minimum = Decimal(str(idea["minimum_to_start"]))
    if monthly_amount < minimum:
        score -= 15
        reasons.append(f"Needs ₹{minimum:,.0f} to start.")
    return {
        "match_score": max(0, min(100, score)),
        "locked": locked,
        "lock_reason": lock_reason,
        "match_reason": " ".join(reasons),
    }


def ideas_for_user(user: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Attach fair match details to every idea and sort the best matches first."""
    ideas = []
    for idea in load_investment_ideas():
        match = match_score(idea, user)
        ideas.append({**idea, **match})
    return sorted(ideas, key=lambda idea: (-idea["match_score"], idea["name"]))
