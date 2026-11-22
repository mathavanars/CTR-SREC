"""Calculate private monthly-amount, expense-limit and growth examples."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from backend.calculators import (
    HUNDRED,
    ZERO,
    _money,
    _non_negative,
    calculate_debt_payoff,
    calculate_emergency_fund_months,
    calculate_goal_chance,
    calculate_plan_growth,
    calculate_sip_future_value_months,
    split_monthly_amount,
    suggest_monthly_amount,
)
from backend.investment_ideas import load_basics_jars, load_investment_ideas
from backend.suggest import build_smart_suggestion


def _catalog() -> dict[str, dict[str, Any]]:
    """Return one lookup for regular ideas and the two basics choices."""
    return {
        str(item["id"]): item
        for item in load_investment_ideas() + load_basics_jars()
    }


def _plain_values(value: Any) -> Any:
    """Turn Decimal values into exact strings before sending data to a page."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain_values(item) for item in value]
    return value


def _round_down_hundred(value: Decimal) -> Decimal:
    """Round a positive amount down to a whole hundred rupees."""
    return (value / Decimal("100")).to_integral_value(rounding=ROUND_DOWN) * Decimal("100")


def _growth_parts(
    amount: Decimal,
    profile: Mapping[str, Any],
    saved_parts: Sequence[Mapping[str, Any]] | None,
    market_snapshot: Mapping[str, Any],
    suggestion: Mapping[str, Any],
) -> list[dict[str, Decimal | str]]:
    """Build the selected plan's exact rupee parts and per-part return ranges."""
    catalog = _catalog()
    if saved_parts is None:
        # Keep the no-plan suggestion stable while users compare different amounts.
        reference_amount = max(Decimal("500"), Decimal(str(suggestion["recommended"])))
        readiness = {
            "ready": bool(suggestion["ready_to_invest"]),
            "emergency_fund_months": calculate_emergency_fund_months(
                profile.get("savings", 0),
                profile.get("expenses", 0),
            ),
            "has_high_interest_debt": any(
                Decimal(str(debt.get("interest_rate", debt.get("annual_rate", 0)))) > Decimal("15")
                for debt in profile.get("debts", [])
            ),
        }
        proposed = build_smart_suggestion(
            reference_amount,
            str(profile.get("investor_type") or "balanced"),
            list(profile.get("goals") or []),
            readiness,
            market_snapshot,
        )
        selected_parts = proposed["parts"]
    else:
        selected_parts = list(saved_parts)

    weighted_parts: list[dict[str, Decimal | str]] = []
    for saved_part in selected_parts:
        share = _non_negative(saved_part.get("share", 0), "Plan share")
        if share == ZERO:
            continue
        idea_id = str(saved_part.get("idea_id", ""))
        idea = catalog.get(idea_id)
        if idea is None:
            raise ValueError("A saved plan idea is no longer available. Please edit your plan.")
        weighted_parts.append({
            "idea_id": idea_id,
            "share": share,
            "expected_return_low": Decimal(str(
                saved_part.get("expected_return_low", idea["expected_return_low"])
            )),
            "expected_return_mid": Decimal(str(
                saved_part.get("expected_return_mid", idea["expected_return_mid"])
            )),
            "expected_return_high": Decimal(str(
                saved_part.get("expected_return_high", idea["expected_return_high"])
            )),
        })

    if not weighted_parts:
        raise ValueError("Choose at least one plan part before projecting growth.")
    if sum((part["share"] for part in weighted_parts), ZERO) != HUNDRED:
        raise ValueError("Saved plan part shares must add up to 100%.")

    amounts = split_monthly_amount(amount, [part["share"] for part in weighted_parts])
    return [
        {
            **part,
            "monthly_amount": monthly_amount,
        }
        for part, monthly_amount in zip(weighted_parts, amounts)
    ]


def _plan_value_for_months(
    amount: Decimal,
    parts: Sequence[Mapping[str, Any]],
    months: int,
) -> Decimal:
    """Add each plan part's own middle-case SIP value for a goal timeline."""
    part_amounts = split_monthly_amount(amount, [part["share"] for part in parts])
    value = sum(
        (
            calculate_sip_future_value_months(
                part_amount,
                part["expected_return_mid"],
                months,
            )
            for part, part_amount in zip(parts, part_amounts)
        ),
        ZERO,
    )
    return _money(value)


def _expense_tips(room_left: Decimal, cushion: Decimal) -> list[str]:
    """Give three number-backed ways to make the monthly budget safer."""
    amount_to_free = _money(max(Decimal("100"), cushion - room_left))
    words = f"Rs {amount_to_free:,.2f}"
    return [
        f"Cut monthly expenses by {words}.",
        f"Raise monthly income by {words}.",
        f"Lower the monthly amount by {words}.",
    ]


def _basics_timeline(
    amount: Decimal,
    profile: Mapping[str, Any],
    expenses: Decimal,
    high_interest_debt: bool,
) -> dict[str, Any]:
    """Estimate emergency-fund timing and extra-payment debt results."""
    savings = _non_negative(profile.get("savings", 0), "Savings")
    emergency_gap = max(ZERO, Decimal("3") * expenses - savings)
    emergency_priority = emergency_gap > ZERO
    emergency_payment = amount
    debt_payment = amount
    if emergency_priority and high_interest_debt:
        emergency_payment = _money(amount / Decimal("2"))
        debt_payment = amount - emergency_payment
    elif emergency_priority:
        debt_payment = ZERO
    elif high_interest_debt:
        emergency_payment = ZERO
    emergency_months = (
        int((emergency_gap / emergency_payment).to_integral_value(rounding=ROUND_CEILING))
        if emergency_payment > ZERO and emergency_gap > ZERO
        else 0 if emergency_gap == ZERO else None
    )

    debts = list(profile.get("debts") or [])
    debt_result = None
    if high_interest_debt:
        total_emi = sum(
            (_non_negative(debt.get("emi", 0), "Debt EMI") for debt in debts),
            ZERO,
        )
        extra_plan = calculate_debt_payoff(
            debts,
            "avalanche",
            extra_monthly=debt_payment,
        ) if debt_payment > ZERO or total_emi > ZERO else None
        base_plan = (
            calculate_debt_payoff(debts, "avalanche")
            if total_emi > ZERO
            else None
        )
        debt_result = {
            "months_with_extra": extra_plan["months"] if extra_plan else None,
            "interest_saved": (
                _money(max(
                    ZERO,
                    Decimal(str(base_plan["total_interest_paid"]))
                    - Decimal(str(extra_plan["total_interest_paid"])),
                ))
                if base_plan is not None and extra_plan is not None
                else None
            ),
        }

    return {
        "emergency_fund_gap": _money(emergency_gap),
        "emergency_fund_months": emergency_months,
        "emergency_fund_monthly_amount": _money(emergency_payment),
        "debt_extra_monthly_amount": _money(debt_payment),
        "debt": debt_result,
    }


def calculate_amount_growth(
    amount: object,
    years: int,
    profile: Mapping[str, Any],
    saved_parts: Sequence[Mapping[str, Any]] | None,
    market_snapshot: Mapping[str, Any],
    expenses_override: object | None = None,
) -> dict[str, Any]:
    """Return a user's amount growth, nearest goal and expense-limit calculations."""
    monthly_amount = _non_negative(amount, "Monthly amount")
    if not 1 <= years <= 30:
        raise ValueError("Years must be a whole number between 1 and 30.")

    income = _non_negative(profile.get("income", 0), "Monthly income")
    expenses = _non_negative(
        expenses_override if expenses_override is not None else profile.get("expenses", 0),
        "Monthly expenses",
    )
    debts = list(profile.get("debts") or [])
    emis = sum(
        (_non_negative(debt.get("emi", 0), "Debt EMI") for debt in debts),
        ZERO,
    )
    suggestion_profile = {
        **profile,
        "income": income,
        "expenses": expenses,
        "debts": debts,
    }
    suggestion = suggest_monthly_amount(suggestion_profile)

    # The expense slider asks the backend to find the leftover amount in whole hundreds.
    expense_preview = expenses_override is not None
    basics_amount = Decimal(str(suggestion["basics"]))
    if expense_preview:
        monthly_amount = _round_down_hundred(
            max(ZERO, income - emis - basics_amount - expenses)
        )

    highest_expenses = income - emis - basics_amount - monthly_amount
    cushion = Decimal(str(suggestion["cushion"]))
    safe_expenses = highest_expenses - cushion
    room_left = highest_expenses - expenses
    nearest_goal = min(
        (
            goal for goal in profile.get("goals", [])
            if goal.get("amount") is not None and goal.get("years") is not None
        ),
        key=lambda goal: int(goal["years"]),
        default=None,
    )
    high_interest_debt = any(
        Decimal(str(debt.get("interest_rate", debt.get("annual_rate", 0)))) > Decimal("15")
        for debt in debts
    )
    no_surplus = Decimal(str(suggestion["surplus"])) <= ZERO
    ready = bool(suggestion["ready_to_invest"]) and not no_surplus
    basics = _basics_timeline(
        monthly_amount,
        suggestion_profile,
        expenses,
        high_interest_debt,
    )
    tips = (
        _expense_tips(room_left, cushion)
        if room_left < cushion or no_surplus
        else list(suggestion["tips"])
    )

    expense_limit = {
        "income": _money(income),
        "total_emi": _money(emis),
        "basics_amount": _money(basics_amount),
        "monthly_amount": _money(monthly_amount),
        "highest_expenses_allowed": _money(highest_expenses),
        "safe_expense_limit": _money(safe_expenses),
        "cushion": _money(cushion),
        "current_expenses": _money(expenses),
        "room_left": _money(room_left),
        "over_by": _money(max(ZERO, -room_left)),
        "slider_min": ZERO,
        "slider_max": _money(income),
        "is_expense_preview": expense_preview,
        "tips": tips,
    }
    stamp = datetime.now(timezone.utc)
    local_time = stamp.astimezone(ZoneInfo("Asia/Kolkata"))
    response: dict[str, Any] = {
        "amount": _money(monthly_amount),
        "years": years,
        "mode": "no_surplus" if no_surplus else "growth" if ready else "basics",
        "message": (
            "There is no money left after expenses and EMI. Try the steps below before investing."
            if no_surplus
            else "This amount goes to your money basics first, not to investments."
            if not ready
            else ""
        ),
        "expense_limit": expense_limit,
        "basics": basics,
        "goal": None,
        "parts": [],
        "totals": None,
        "series": [],
        "tips": tips,
        "calculated_at": stamp.isoformat().replace("+00:00", "Z"),
        "calculated_at_local": (
            f"{local_time.strftime('%d %b %Y')}, "
            f"{local_time.strftime('%I:%M %p').lstrip('0')}"
        ),
        "label": "Expected, not guaranteed. These are possible outcomes, not promises.",
    }
    if no_surplus or not ready:
        return _plain_values(response)

    growth_parts = _growth_parts(
        monthly_amount,
        suggestion_profile,
        saved_parts,
        market_snapshot,
        suggestion,
    )
    series = []
    for year in range(1, 31):
        totals = calculate_plan_growth(growth_parts, year)
        series.append({
            "year": year,
            **totals,
        })
    selected_totals = series[years - 1]

    if nearest_goal is not None:
        goal_years = int(nearest_goal["years"])
        goal_amount = Decimal(str(nearest_goal["amount"]))
        goal_value = calculate_plan_growth(growth_parts, goal_years)["mid"]
        months_needed = next(
            (
                month
                for month in range(1, 601)
                if _plan_value_for_months(monthly_amount, growth_parts, month) >= goal_amount
            ),
            None,
        )
        response["goal"] = {
            "name": str(nearest_goal["name"]),
            "target": _money(goal_amount),
            "goal_chance": calculate_goal_chance(goal_value, goal_amount),
            "years_to_reach": (
                _money(Decimal(months_needed) / Decimal("12"))
                if months_needed is not None
                else None
            ),
            "months_to_reach": months_needed,
        }

    response.update({
        "parts": [
            {
                "idea_id": part["idea_id"],
                "share": part["share"],
                "monthly_amount": part["monthly_amount"],
                "expected_return_low": part["expected_return_low"],
                "expected_return_mid": part["expected_return_mid"],
                "expected_return_high": part["expected_return_high"],
            }
            for part in growth_parts
        ],
        "totals": selected_totals,
        "series": series,
    })
    return _plain_values(response)
