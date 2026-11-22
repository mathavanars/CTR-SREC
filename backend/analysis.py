"""Check a saved plan and explain its strengths and possible fixes."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from backend.calculators import (
    calculate_goal_chance,
    calculate_money_left_after_debts,
    calculate_plan_future_value_months,
    calculate_plan_growth,
    calculate_readiness,
    calculate_required_plan_sip,
    max_parts,
    split_monthly_amount,
)
from backend.investment_ideas import load_basics_jars, load_investment_ideas


ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _catalog() -> dict[str, dict[str, Any]]:
    """Make one lookup table for investment ideas and safe basics jars."""
    ideas = load_investment_ideas() + load_basics_jars()
    return {str(idea["id"]): idea for idea in ideas}


def _plan_facts(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Add trusted catalog facts and exact monthly amounts to every saved part."""
    parts = list(plan.get("parts") or [])
    amounts = split_monthly_amount(
        plan.get("monthly_amount", 0),
        [part.get("share", 0) for part in parts],
    )
    ideas = _catalog()
    result = []
    for part, amount in zip(parts, amounts):
        idea_id = str(part.get("idea_id", ""))
        if idea_id not in ideas:
            raise ValueError(f"We could not find the idea named {idea_id}.")
        idea = ideas[idea_id]
        result.append({
            **idea,
            "idea_id": idea_id,
            "share": Decimal(str(part["share"])),
            "monthly_amount": amount,
        })
    return result


def _grade(score: int) -> str:
    """Turn a plan score into its short, friendly grade."""
    if score >= 85:
        return "Strong"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Needs work"
    return "Risky"


def _score_points(value: Decimal) -> int:
    """Round one check's points to a whole number for a simple scorecard."""
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _risk_range(investor_type: str) -> tuple[Decimal, Decimal]:
    """Return the comfortable weighted-risk range for one quiz result."""
    ranges = {
        "conservative": (Decimal("1.0"), Decimal("2.2")),
        "balanced": (Decimal("2.2"), Decimal("3.5")),
        "aggressive": (Decimal("3.5"), Decimal("5.0")),
    }
    return ranges.get(investor_type.lower(), ranges["balanced"])


def _make_check(
    check_id: str,
    name: str,
    status: str,
    score: int,
    maximum: int,
    message: str,
) -> dict[str, Any]:
    """Create one check result with the same simple response shape."""
    return {
        "id": check_id,
        "name": name,
        "status": status,
        "score": score,
        "max_points": maximum,
        "points_lost": maximum - score,
        "message": message,
    }


def analyze_plan(user: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    """Score diversification, risk, time, affordability, minimums and goal progress."""
    parts = _plan_facts(plan)
    if not parts:
        raise ValueError("Choose at least one idea before reviewing your plan.")
    monthly_amount = Decimal(str(plan["monthly_amount"]))
    share_total = sum((part["share"] for part in parts), ZERO)
    if share_total != HUNDRED:
        raise ValueError("Your parts must add up to exactly 100%.")

    active_parts = [part for part in parts if part["share"] > ZERO]
    classes = {str(part["asset_class"]) for part in active_parts}
    largest_share = max(part["share"] for part in active_parts)
    if len(active_parts) == 1:
        diversification = _make_check(
            "diversification", "Spread across different jars", "problem", 0, 25,
            "One part holds all your money. Try spreading it across different kinds of jars.",
        )
    elif len(classes) >= 3 and largest_share <= Decimal("40"):
        diversification = _make_check(
            "diversification", "Spread across different jars", "good", 25, 25,
            f"Your plan uses {len(classes)} kinds of jars and no idea has more than 40%.",
        )
    elif largest_share > Decimal("60"):
        diversification = _make_check(
            "diversification", "Spread across different jars", "warning", 5, 25,
            "You are keeping most eggs in one basket. Try spreading the money more evenly.",
        )
    else:
        points = 15 if len(classes) >= 2 else 8
        diversification = _make_check(
            "diversification", "Spread across different jars", "warning", points, 25,
            f"Your plan uses {len(classes)} kinds of jars. Three or more can spread the risk further.",
        )

    investor_type = str(user.get("investor_type") or "balanced").lower()
    lower_risk, upper_risk = _risk_range(investor_type)
    weighted_risk = sum(
        (part["share"] * Decimal(str(part["risk_level"])) for part in parts),
        ZERO,
    ) / HUNDRED
    if lower_risk <= weighted_risk <= upper_risk:
        risk_fit = _make_check(
            "risk-fit", "Fit with your comfort level", "good", 30, 30,
            f"Your weighted risk is {weighted_risk:.2f}, inside the {investor_type.title()} range.",
        )
    else:
        distance = lower_risk - weighted_risk if weighted_risk < lower_risk else weighted_risk - upper_risk
        available = lower_risk - Decimal("1") if weighted_risk < lower_risk else Decimal("5") - upper_risk
        fraction = min(Decimal("1"), distance / available) if available else Decimal("1")
        points = _score_points(Decimal("30") * (Decimal("1") - fraction))
        direction = "safer" if weighted_risk < lower_risk else "riskier"
        risk_fit = _make_check(
            "risk-fit", "Fit with your comfort level", "warning", points, 30,
            f"Your plan is {direction} than the range that matches your {investor_type.title()} answers.",
        )

    goals = list(user.get("goals") or [])
    nearest_goal = min(goals, key=lambda goal: int(goal.get("years", 50)), default=None)
    equity_share = sum(
        (part["share"] for part in parts if part["asset_class"] == "Equity"),
        ZERO,
    )
    locked_ids = {"ppf", "elss", "nps"}
    locked_share = sum(
        (part["share"] for part in parts if part["idea_id"] in locked_ids),
        ZERO,
    )
    time_messages = []
    if nearest_goal:
        goal_years = int(nearest_goal["years"])
        if goal_years < 3 and equity_share > Decimal("30"):
            time_messages.append(
                "Shares can fall in the short term. Money needed soon should stay safer."
            )
        if goal_years < 5 and locked_share > Decimal("50"):
            time_messages.append(
                "Locked money cannot be taken out when you need it."
            )
    time_points = max(0, 20 - 10 * len(time_messages))
    time_fit = _make_check(
        "time-fit",
        "Fit with your goal date",
        "warning" if time_messages else "good",
        time_points,
        20,
        " ".join(time_messages) if time_messages else "Your choices fit the goal date you shared.",
    )

    income = user.get("income") or "1"
    expenses = user.get("expenses") or "0"
    savings = user.get("savings") or "0"
    debts = list(user.get("debts") or [])
    safe_amount = calculate_money_left_after_debts(income, expenses, debts)
    readiness = calculate_readiness(income, expenses, savings, debts)
    emergency_ready = Decimal(str(expenses)) == ZERO or Decimal(
        str(readiness["emergency_fund_months"])
    ) >= Decimal("3")
    amount_affordable = monthly_amount <= safe_amount
    if emergency_ready and amount_affordable:
        affordability_points = 15
        affordability_status = "good"
        affordability_message = "This amount fits your money left and your emergency savings."
    else:
        affordability_points = 0 if not emergency_ready else 7
        affordability_status = "problem" if not emergency_ready else "warning"
        affordability_messages = []
        if not amount_affordable:
            affordability_messages.append(
                "This amount is more than you have left each month."
            )
        if not emergency_ready:
            affordability_messages.append(
                "Build emergency savings for at least 3 months before taking investment risk."
            )
        affordability_message = " ".join(affordability_messages)
    affordability = _make_check(
        "affordability", "Fit your monthly budget", affordability_status,
        affordability_points, 15, affordability_message,
    )

    below_minimum = [
        part for part in parts
        if part["monthly_amount"] < Decimal(str(part["minimum_to_start"]))
    ]
    minimum_score = 10 if not below_minimum else max(0, 10 - 2 * len(below_minimum))
    minimums = _make_check(
        "minimums",
        "Enough to start each part",
        "good" if not below_minimum else "warning",
        minimum_score,
        10,
        "Every part meets its starting minimum."
        if not below_minimum
        else "Some parts are below their starting minimum. You may need at least "
        + ", ".join(
            f"₹{part['minimum_to_start']} for {part['name']}"
            for part in below_minimum
        )
        + ".",
    )

    checks = [diversification, risk_fit, time_fit, affordability, minimums]
    score = sum(check["score"] for check in checks)
    growth = {
        str(years): calculate_plan_growth(parts, years)
        for years in (5, 10)
    }
    average_rate = sum(
        (
            part["share"] * Decimal(str(part["expected_return_mid"]))
            for part in parts
        ),
        ZERO,
    ) / HUNDRED
    goal_result: dict[str, Any] | None = None
    if nearest_goal:
        goal_amount = Decimal(str(nearest_goal["amount"]))
        goal_years = int(nearest_goal["years"])
        goal_mid = calculate_plan_growth(parts, goal_years)["mid"]
        chance = calculate_goal_chance(goal_mid, goal_amount)
        required_monthly = calculate_required_plan_sip(goal_amount, parts, goal_years)
        needed_months = None
        for months in range(1, 601):
            estimate = calculate_plan_future_value_months(
                monthly_amount, parts, months, "mid"
            )
            if estimate >= goal_amount:
                needed_months = months
                break
        goal_result = {
            "name": str(nearest_goal["name"]),
            "amount": goal_amount,
            "years": goal_years,
            "future_value_low": calculate_plan_growth(parts, goal_years)["low"],
            "future_value_mid": goal_mid,
            "future_value_high": calculate_plan_growth(parts, goal_years)["high"],
            "chance_percent": chance,
            "reachable": goal_mid >= goal_amount,
            "options": {
                "invest_more_monthly": required_monthly,
                "take_more_time_years": (
                    (needed_months + 11) // 12 if needed_months is not None else None
                ),
                "lower_goal_to": goal_mid,
            },
        }

    return {
        "score": score,
        "grade": _grade(score),
        "weighted_risk": weighted_risk,
        "weighted_average_return": average_rate,
        "weighted_average_return_label": "Average, for information only",
        "monthly_amount": monthly_amount,
        "safe_monthly_amount": safe_amount,
        "checks": checks,
        "top_fixes": suggest_fixes(user, plan, checks, parts, safe_amount),
        "growth": growth,
        "goal": goal_result,
        "label": "Expected, not guaranteed",
    }


def suggest_fixes(
    user: Mapping[str, Any],
    plan: Mapping[str, Any],
    checks: list[dict[str, Any]],
    facts: list[dict[str, Any]] | None = None,
    safe_amount: Decimal | None = None,
) -> list[dict[str, Any]]:
    """Suggest up to three concrete plan changes, sorted by points lost."""
    parts = facts if facts is not None else _plan_facts(plan)
    safe = safe_amount
    if safe is None:
        safe = calculate_money_left_after_debts(
            user.get("income") or "1",
            user.get("expenses") or "0",
            user.get("debts") or [],
        )
    current_amount = Decimal(str(plan.get("monthly_amount", 0)))
    catalog = _catalog()
    candidates = []
    for check in checks:
        if check["points_lost"] <= 0:
            continue
        fix_parts = [
            {"idea_id": part["idea_id"], "share": part["share"]}
            for part in parts
        ]
        fix_amount = current_amount
        label = ""
        if check["id"] == "affordability" and safe > ZERO:
            fix_amount = min(current_amount, safe)
            label = f"Set the monthly amount to ₹{fix_amount:,.2f} to fit your budget."
        elif check["id"] == "minimums":
            amounts = split_monthly_amount(
                current_amount, [part["share"] for part in parts]
            )
            too_small = [
                index for index, part in enumerate(parts)
                if amounts[index] < Decimal(str(part["minimum_to_start"]))
            ]
            if too_small and len(parts) > 1:
                largest_index = max(range(len(parts)), key=amounts.__getitem__)
                fix_parts = [{
                    "idea_id": fix_parts[largest_index]["idea_id"],
                    "share": HUNDRED,
                }]
                label = "Combine the small parts into one larger part to meet its starting minimum."
        else:
            high_risk_index = max(
                (index for index, part in enumerate(parts) if part["share"] > ZERO),
                key=lambda index: (
                    Decimal(str(parts[index]["risk_level"])),
                    parts[index]["share"],
                ),
            )
            source = parts[high_risk_index]
            target_id = "gold" if check["id"] == "diversification" else "fd-rd"
            if target_id not in catalog:
                continue
            target_index = next(
                (index for index, part in enumerate(parts) if part["idea_id"] == target_id),
                None,
            )
            if target_index is None and len(fix_parts) >= min(7, max_parts(current_amount)):
                safer_targets = [
                    index for index, part in enumerate(parts)
                    if index != high_risk_index
                    and Decimal(str(part["risk_level"])) < Decimal(str(source["risk_level"]))
                ]
                if safer_targets:
                    target_index = min(
                        safer_targets,
                        key=lambda index: Decimal(str(parts[index]["risk_level"])),
                    )
                    target_id = parts[target_index]["idea_id"]
            move = min(Decimal("20"), fix_parts[high_risk_index]["share"])
            if move <= ZERO or source["idea_id"] == target_id:
                continue
            fix_parts[high_risk_index]["share"] -= move
            if target_index is None:
                if len(fix_parts) >= min(7, max_parts(current_amount)) and fix_parts[high_risk_index]["share"] == ZERO:
                    fix_parts.pop(high_risk_index)
                    fix_parts.append({"idea_id": target_id, "share": move})
                elif len(fix_parts) >= min(7, max_parts(current_amount)):
                    continue
                else:
                    fix_parts.append({"idea_id": target_id, "share": move})
            else:
                fix_parts[target_index]["share"] += move
            target_name = catalog[target_id]["name"]
            label = (
                f"Move {move}% from {source['name']} to {target_name} "
                "to spread or lower risk."
            )
        if not label:
            continue
        candidates.append({
            "id": check["id"],
            "label": label,
            "points_lost": check["points_lost"],
            "monthly_amount": fix_amount,
            "parts": fix_parts,
        })
    candidates.sort(key=lambda fix: fix["points_lost"], reverse=True)
    return candidates[:3]
