"""Keep every money calculation in one clear Decimal-based module.

This file handles education calculations only. Its results are assumptions,
not promises of profit or professional financial advice.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP
from datetime import date, datetime, timezone
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from backend.suggestion_config import (
    ASSET_RISK,
    BASE_MIXES,
    DEFAULT_ANNUAL_STEP_UP_PERCENT,
    DEFAULT_GOAL_RETURN_RATE,
    INCOME_STABILITY_MULTIPLIERS,
    MONTHLY_AMOUNT_SHARES,
    RISK_RANGES,
    STRESS_SHOCKS,
)


MONEY = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _decimal(value: object, label: str) -> Decimal:
    """Convert one input to Decimal and return it with a friendly name."""
    try:
        # Text and number inputs become Decimal without introducing float rounding.
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Please enter a valid number for {label}.")


def _money(value: Decimal) -> Decimal:
    """Round only at the final money step to two decimal places."""
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def round_money(value: object) -> Decimal:
    """Round one exact money value to paise."""
    return _money(_decimal(value, "Money amount"))


def _non_negative(value: object, label: str) -> Decimal:
    """Check that a money or count input is zero or more."""
    result = _decimal(value, label)
    if result < ZERO:
        raise ValueError(f"{label} cannot be negative.")
    return result


def _positive(value: object, label: str) -> Decimal:
    """Check that a required income or goal is more than zero."""
    result = _decimal(value, label)
    if result <= ZERO:
        raise ValueError(f"{label} must be greater than 0.")
    return result


def _years(value: object) -> int:
    """Accept whole years from 1 through 50, because longer plans are not supported."""
    try:
        # An integer makes the month and compound periods exact.
        years = int(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Years must be a whole number between 1 and 50.")
    if Decimal(years) != Decimal(str(value)):
        raise ValueError("Years must be a whole number between 1 and 50.")
    if years < 1 or years > 50:
        raise ValueError("Years must be between 1 and 50.")
    return years


def _rate(value: object) -> Decimal:
    """Check an annual return rate between 0% and 40%."""
    rate = _decimal(value, "Annual return rate")
    if rate < ZERO or rate > Decimal("40"):
        raise ValueError("Annual return rate must be between 0 and 40.")
    return rate


def _sip_value_for_months(principal: Decimal, rate: Decimal, months: int) -> Decimal:
    """Calculate one SIP value from already-checked money, rate and month inputs."""
    if principal == ZERO:
        return ZERO.quantize(MONEY)
    if rate == ZERO:
        # With no growth, the money is simply the monthly amount repeated for every month.
        result = principal * Decimal(months)
    else:
        # r is the monthly rate: yearly rate divided by 12 and then by 100.
        r = rate / Decimal("12") / HUNDRED
        growth_factor = (Decimal("1") + r) ** months
        # SIP adds one payment at the start of each month, so the extra (1+r) is included.
        result = principal * ((growth_factor - Decimal("1")) / r) * (Decimal("1") + r)
    return _money(result)


def calculate_sip_future_value(monthly_amount: object, annual_rate: object, years: object) -> Decimal:
    """Calculate SIP value: monthly amount, annual assumed rate and years go in; future value comes out.

    The value is an estimate, not a guaranteed result.
    """
    principal = _non_negative(monthly_amount, "Monthly amount")
    rate = _rate(annual_rate)
    whole_years = _years(years)
    return _sip_value_for_months(principal, rate, whole_years * 12)


def calculate_sip_future_value_months(
    monthly_amount: object,
    annual_rate: object,
    months: object,
) -> Decimal:
    """Calculate a SIP estimate for a whole number of months, up to fifty years."""
    principal = _non_negative(monthly_amount, "Monthly amount")
    rate = _rate(annual_rate)
    try:
        month_count = int(Decimal(str(months)))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Months must be a whole number from 1 to 600.")
    if Decimal(month_count) != Decimal(str(months)) or not 1 <= month_count <= 600:
        raise ValueError("Months must be a whole number from 1 to 600.")
    return _sip_value_for_months(principal, rate, month_count)


def max_parts(monthly_amount: object) -> int:
    """Return the requested upper part limit for one monthly amount."""
    amount = _non_negative(monthly_amount, "Monthly amount")
    if amount < Decimal("1000"):
        return 2
    if amount < Decimal("3000"):
        return 3
    if amount < Decimal("8000"):
        return 5
    return 7


def _weighted_asset_risk(mix: Mapping[str, Decimal]) -> Decimal:
    """Calculate one plan risk score from its four asset-group percentages."""
    return sum(
        (mix[name] * Decimal(str(ASSET_RISK[name])) for name in ASSET_RISK),
        ZERO,
    ) / HUNDRED


def calculate_smart_mix(
    investor_type: str,
    market_snapshot: Mapping[str, object],
    nearest_goal_years: int | None = None,
) -> dict[str, object]:
    """Apply goal limits and checked market tilts to a Decimal-based starting mix."""
    key = investor_type.lower()
    if key not in BASE_MIXES:
        raise ValueError("Investor type must be conservative, balanced or aggressive.")
    base = {name: Decimal(value) for name, value in BASE_MIXES[key].items()}
    mix = dict(base)
    goal_adjustment = None
    if nearest_goal_years is not None and nearest_goal_years < 5:
        equity_cap = Decimal("20") if nearest_goal_years < 3 else Decimal("50")
        if mix["equity"] > equity_cap:
            shifted = mix["equity"] - equity_cap
            mix["equity"] = equity_cap
            mix["debt"] += shifted
            goal_adjustment = (
                f"Equity was capped at {equity_cap}% because your nearest goal is "
                f"{nearest_goal_years} years away; the rest moved to debt."
            )
    goal_mix = dict(mix)
    lower_risk, upper_risk = (
        Decimal(str(value)) for value in RISK_RANGES[key]
    )
    starting_risk = _weighted_asset_risk(mix)
    starting_risk_in_range = lower_risk <= starting_risk <= upper_risk
    tilts: list[str] = []

    def apply_tilt(name: str, changes: Mapping[str, Decimal], explanation: str) -> None:
        """Apply one market change only when it stays within the stated risk rules."""
        before = dict(mix)
        candidate = dict(mix)
        for asset, change in changes.items():
            candidate[asset] += change
        within_bounds = (
            all(value >= ZERO for value in candidate.values())
            and sum(candidate.values(), ZERO) == HUNDRED
            and Decimal("5") <= candidate["gold"] <= Decimal("10")
            and all(abs(candidate[asset] - goal_mix[asset]) <= Decimal("10") for asset in candidate)
        )
        candidate_risk = _weighted_asset_risk(candidate)
        risk_ok = (
            lower_risk <= candidate_risk <= upper_risk
            if starting_risk_in_range
            else candidate_risk == starting_risk
        )
        if within_bounds and risk_ok:
            mix.update(candidate)
            tilts.append(f"{name}: {explanation}")
        else:
            tilts.append(f"{name}: not applied because it would break the mix or risk limits.")
        if not within_bounds or not risk_ok:
            mix.update(before)

    metrics = market_snapshot.get("metrics", {})
    if not isinstance(metrics, Mapping):
        raise ValueError("Market data is not available for a safe plan.")

    def metric_value(name: str) -> Decimal:
        """Read a validated market value as Decimal, without using float math."""
        entry = metrics.get(name)
        if not isinstance(entry, Mapping) or "value" not in entry:
            raise ValueError(f"Market data is missing {name.replace('_', ' ')}.")
        return _decimal(entry["value"], name.replace("_", " "))

    # A non-positive FD return after inflation moves five points from cash to debt.
    if metric_value("sbi_1y_fd_rate") - metric_value("cpi_inflation") <= ZERO:
        apply_tilt(
            "Deposit and inflation",
            {"cash": Decimal("-5"), "debt": Decimal("5")},
            "cash fell 5 points and debt rose 5 because the deposit rate does not beat inflation.",
        )
    # A high Nifty valuation shifts five points from equity to debt; a low one does the reverse.
    nifty_pe = metric_value("nifty_pe")
    nifty_average = metric_value("nifty_pe_10y_average")
    if nifty_pe > nifty_average * Decimal("1.20"):
        apply_tilt(
            "Nifty valuation",
            {"equity": Decimal("-5"), "debt": Decimal("5")},
            "equity fell 5 points and debt rose 5 because Nifty P/E is over 20% above its average.",
        )
    elif nifty_pe < nifty_average * Decimal("0.90"):
        apply_tilt(
            "Nifty valuation",
            {"equity": Decimal("5"), "debt": Decimal("-5")},
            "equity rose 5 points because Nifty P/E is over 10% below its average.",
        )
    # Rate cuts favor debt funds in this example; rate rises favor deposits instead.
    repo_entry = metrics.get("repo_rate", {})
    repo_direction = str(repo_entry.get("direction", "steady")) if isinstance(repo_entry, Mapping) else "steady"
    if repo_direction == "falling":
        apply_tilt(
            "RBI rate direction",
            {"cash": Decimal("-5"), "debt": Decimal("5")},
            "debt rose 5 points because RBI rates are falling.",
        )
    elif repo_direction == "rising":
        apply_tilt(
            "RBI rate direction",
            {"debt": Decimal("-5"), "cash": Decimal("5")},
            "FD/RD cash rose 5 points because RBI rates are rising.",
        )
    # A strong one-year gold rise trims its share by three points and keeps it within 5–10%.
    if metric_value("gold_1y_change") > Decimal("25"):
        apply_tilt(
            "Gold price change",
            {"gold": Decimal("-3"), "debt": Decimal("3")},
            "gold fell 3 points after a rise above 25% in one year.",
        )

    final_risk = _weighted_asset_risk(mix)
    risk_exception = not (lower_risk <= final_risk <= upper_risk)
    return {
        "investor_type": key,
        "base_mix": base,
        "mix": mix,
        "goal_adjustment": goal_adjustment,
        "tilts": tilts,
        "weighted_risk": final_risk,
        "risk_range": {"low": lower_risk, "high": upper_risk},
        "risk_band_exception": risk_exception,
    }


def calculate_stress_test(
    monthly_amount: object,
    parts: Sequence[Mapping[str, object]],
) -> dict[str, Decimal | str]:
    """Estimate one bad-year loss by adding the shock for every separate plan part."""
    amount = _money(_non_negative(monthly_amount, "Monthly amount"))
    loss_percent = ZERO
    for part in parts:
        share = _non_negative(part.get("share", 0), "Part share")
        idea_id = str(part.get("idea_id", ""))
        asset_class = str(part.get("asset_class", "")).lower()
        if idea_id in {"index-sip", "equity-funds", "elss", "direct-stocks"} or asset_class == "equity":
            shock = Decimal(str(STRESS_SHOCKS["equity"]))
        elif idea_id == "debt-fund":
            shock = Decimal(str(STRESS_SHOCKS["debt-fund"]))
        elif asset_class == "gold" or idea_id == "gold":
            shock = Decimal(str(STRESS_SHOCKS["gold"]))
        else:
            shock = Decimal(str(STRESS_SHOCKS["no_drop"]))
        loss_percent += share * abs(min(ZERO, shock)) / HUNDRED
    return {
        "fall_percent": _money(loss_percent),
        "loss_amount": _money(amount * loss_percent / HUNDRED),
        "label": "One bad-year example, not a prediction.",
    }


def normalize_shares(shares: Sequence[object]) -> list[Decimal]:
    """Scale positive percentage weights to exactly 100%, with two decimal places."""
    weights = [_non_negative(share, "Part share") for share in shares]
    total = sum(weights, ZERO)
    if not weights or total <= ZERO:
        raise ValueError("Choose at least one part with a positive share.")
    normalized = [_money(weight * HUNDRED / total) for weight in weights]
    difference = HUNDRED - sum(normalized, ZERO)
    largest_index = max(range(len(weights)), key=weights.__getitem__)
    normalized[largest_index] += difference
    return normalized


def split_monthly_amount(monthly_amount: object, shares: Sequence[object]) -> list[Decimal]:
    """Split an exact monthly amount by percentages and put rounding paise on the largest share."""
    amount = _money(_non_negative(monthly_amount, "Monthly amount"))
    if not shares or len(shares) > 7:
        raise ValueError("Choose between 1 and 7 parts.")
    percentages = [_non_negative(share, "Part share") for share in shares]
    total_share = sum(percentages, ZERO)
    if total_share != HUNDRED:
        raise ValueError(
            f"Your parts add up to {_money(total_share)}%. Make the total exactly 100%."
        )
    amounts = [_money(amount * share / HUNDRED) for share in percentages]
    difference = amount - sum(amounts, ZERO)
    if difference != ZERO:
        largest_index = max(range(len(percentages)), key=percentages.__getitem__)
        amounts[largest_index] += difference
    return amounts


def calculate_preview_amounts(monthly_amount: object, shares: Sequence[object]) -> list[Decimal]:
    """Calculate live slider amounts before the user's shares total 100%."""
    amount = _money(_non_negative(monthly_amount, "Monthly amount"))
    if not shares or len(shares) > 7:
        raise ValueError("Choose between 1 and 7 parts.")
    percentages = [_non_negative(share, "Part share") for share in shares]
    return [_money(amount * share / HUNDRED) for share in percentages]


def calculate_safe_monthly_amount(
    income: object,
    expenses: object,
    total_emis: object,
) -> Decimal:
    """Find money left each month after expenses and all debt EMIs."""
    return _money(
        _positive(income, "Monthly income")
        - _non_negative(expenses, "Monthly expenses")
        - _non_negative(total_emis, "Total monthly EMIs")
    )


def calculate_money_left_after_debts(
    income: object,
    expenses: object,
    debts: Iterable[Mapping[str, object]],
) -> Decimal:
    """Find money left each month after adding every saved debt EMI."""
    total_emis = sum(
        (_non_negative(debt.get("emi", 0), "Debt EMI") for debt in debts),
        ZERO,
    )
    return calculate_safe_monthly_amount(income, expenses, total_emis)


def calculate_plan_growth(parts: Sequence[Mapping[str, object]], years: object) -> dict[str, Decimal]:
    """Add each part's own low, middle and high SIP estimates for one time period."""
    whole_years = _years(years)
    totals = {"low": ZERO, "mid": ZERO, "high": ZERO}
    monthly_total = ZERO
    for part in parts:
        monthly_amount = _non_negative(part.get("monthly_amount", 0), "Part amount")
        monthly_total += monthly_amount
        for level in totals:
            rate = part.get(f"expected_return_{level}", part.get(f"{level}_rate", 0))
            totals[level] += calculate_sip_future_value(monthly_amount, rate, whole_years)
    invested = monthly_total * Decimal(whole_years * 12)
    result = {level: _money(value) for level, value in totals.items()}
    result["invested"] = _money(invested)
    result["earned_low"] = _money(max(ZERO, result["low"] - invested))
    result["earned_mid"] = _money(max(ZERO, result["mid"] - invested))
    result["earned_high"] = _money(max(ZERO, result["high"] - invested))
    return result


def calculate_required_plan_sip(
    goal_amount: object,
    parts: Sequence[Mapping[str, object]],
    years: object,
) -> Decimal:
    """Find total monthly SIP needed when each part keeps its own assumed middle return."""
    whole_years = _years(years)
    share_total = sum((_non_negative(part.get("share", 0), "Part share") for part in parts), ZERO)
    if not parts or share_total != HUNDRED:
        raise ValueError("Plan shares must add up to 100% before a goal amount can be planned.")
    required = ZERO
    for part in parts:
        part_share = _non_negative(part.get("share", 0), "Part share")
        rate = part.get("expected_return_mid", part.get("mid_rate", 0))
        required += calculate_required_monthly_sip(goal_amount, rate, whole_years) * part_share / HUNDRED
    return _money(required)


def calculate_plan_future_value_months(
    monthly_amount: object,
    parts: Sequence[Mapping[str, object]],
    months: int,
    level: str = "mid",
) -> Decimal:
    """Add part-by-part SIP estimates for a whole-month period and one return range."""
    if level not in {"low", "mid", "high"}:
        raise ValueError("Return range must be low, mid or high.")
    shares = [part.get("share", 0) for part in parts]
    amounts = split_monthly_amount(monthly_amount, shares)
    total = ZERO
    for amount, part in zip(amounts, parts):
        rate = part.get(f"expected_return_{level}", part.get(f"{level}_rate", 0))
        total += calculate_sip_future_value_months(amount, rate, months)
    return _money(total)


def calculate_goal_chance(future_value: object, goal_amount: object) -> Decimal:
    """Compare an estimated future value with a goal and cap its chance display at 100%."""
    future = _non_negative(future_value, "Future value")
    goal = _positive(goal_amount, "Goal amount")
    return _money(min(HUNDRED, future / goal * HUNDRED))


def calculate_step_up_sip_future_value(
    monthly_amount: object,
    annual_rate: object,
    months: object,
    annual_step_up_percent: object = DEFAULT_ANNUAL_STEP_UP_PERCENT,
) -> Decimal:
    """Grow one monthly SIP month by month, raising its payment once each year."""
    amount = _non_negative(monthly_amount, "Monthly amount")
    rate = _rate(annual_rate)
    step_up = _non_negative(annual_step_up_percent, "Annual step-up")
    if step_up > HUNDRED:
        raise ValueError("Annual step-up must be 100% or less.")
    try:
        month_count = int(Decimal(str(months)))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Months must be a whole number from 0 to 600.")
    if Decimal(month_count) != Decimal(str(months)) or not 0 <= month_count <= 600:
        raise ValueError("Months must be a whole number from 0 to 600.")
    if month_count == 0 or amount == ZERO:
        return ZERO.quantize(MONEY)
    monthly_rate = rate / Decimal("12") / HUNDRED
    step_up_factor = Decimal("1") + step_up / HUNDRED
    future_value = ZERO
    for month_index in range(month_count):
        payment = amount * (step_up_factor ** (month_index // 12))
        months_to_grow = month_count - month_index
        future_value += payment * ((Decimal("1") + monthly_rate) ** months_to_grow)
    return _money(future_value)


def calculate_step_up_plan_future_value(
    monthly_amount: object,
    parts: Sequence[Mapping[str, object]],
    months: object,
    level: str = "mid",
    annual_step_up_percent: object = DEFAULT_ANNUAL_STEP_UP_PERCENT,
) -> Decimal:
    """Add separate month-by-month step-up growth for every saved plan part."""
    if level not in {"low", "mid", "high"}:
        raise ValueError("Return range must be low, mid or high.")
    if not parts:
        raise ValueError("Choose saved plan parts before calculating plan growth.")
    part_amounts = split_monthly_amount(monthly_amount, [part.get("share", 0) for part in parts])
    total = ZERO
    for amount, part in zip(part_amounts, parts):
        rate = part.get(f"expected_return_{level}", part.get(f"{level}_rate", 0))
        total += calculate_step_up_sip_future_value(
            amount,
            rate,
            months,
            annual_step_up_percent,
        )
    return _money(total)


def calculate_required_monthly_plan_sip(
    goal_amount: object,
    parts: Sequence[Mapping[str, object]],
    years: object,
) -> Decimal:
    """Solve the needed monthly amount by testing the separate returns in a saved plan."""
    goal = _positive(goal_amount, "Goal amount")
    whole_years = _years(years)
    if not parts:
        raise ValueError("Choose saved plan parts before calculating a goal amount.")
    share_total = sum((_non_negative(part.get("share", 0), "Part share") for part in parts), ZERO)
    if share_total != HUNDRED:
        raise ValueError("Plan shares must add up to 100% before a goal amount can be planned.")
    low = ZERO
    high = goal
    for _ in range(64):
        middle = (low + high) / Decimal("2")
        future_value = calculate_plan_future_value_months(middle, parts, whole_years * 12)
        if future_value >= goal:
            high = middle
        else:
            low = middle
    return _money(high)


def _round_down_hundred(value: Decimal) -> Decimal:
    """Round a non-negative suggestion down to a whole hundred rupees."""
    hundreds = (value / Decimal("100")).to_integral_value(rounding=ROUND_DOWN)
    return hundreds * Decimal("100")


def suggest_monthly_amount(profile: Mapping[str, object]) -> dict[str, object]:
    """Compare what a user wants, can afford and needs using checked Decimal rules."""
    income = _non_negative(profile.get("income", 0), "Monthly income")
    expenses = _non_negative(profile.get("expenses", 0), "Monthly expenses")
    savings = _non_negative(profile.get("savings", 0), "Savings")
    debts = list(profile.get("debts") or [])
    goals = list(profile.get("goals") or [])
    stability = str(profile.get("income_stability") or "steady")
    if stability not in INCOME_STABILITY_MULTIPLIERS:
        raise ValueError("Choose steady, sometimes changing or irregular income.")
    multiplier = INCOME_STABILITY_MULTIPLIERS[stability]
    emis = sum((_non_negative(debt.get("emi", 0), "Debt EMI") for debt in debts), ZERO)
    surplus = income - expenses - emis
    available = max(ZERO, surplus)
    comfortable = _round_down_hundred(
        available * MONTHLY_AMOUNT_SHARES["comfortable"] * multiplier
    )
    recommended = _round_down_hundred(
        available * MONTHLY_AMOUNT_SHARES["recommended"] * multiplier
    )
    stretch = _round_down_hundred(
        available * MONTHLY_AMOUNT_SHARES["stretch"] * multiplier
    )
    emergency_months = calculate_emergency_fund_months(savings, expenses)
    high_interest_debt = any(
        _decimal(debt.get("interest_rate", debt.get("annual_rate", 0)), "Debt interest rate")
        > Decimal("15")
        for debt in debts
    )
    not_ready = (expenses > ZERO and emergency_months < Decimal("3")) or high_interest_debt
    invest_amount = ZERO if not_ready else recommended
    basics_amount = recommended if not_ready else ZERO
    emergency_gap = max(ZERO, Decimal("3") * expenses - savings)
    emergency_build_months = None
    if basics_amount > ZERO:
        emergency_build_months = int(
            (emergency_gap / basics_amount).to_integral_value(rounding=ROUND_CEILING)
        )
    wanted_value = profile.get("wanted_monthly_amount")
    if wanted_value is None:
        wanted_value = profile.get("monthly_amount")
    wanted = _non_negative(wanted_value if wanted_value is not None else recommended, "Wanted monthly amount")
    if wanted <= comfortable:
        verdict = "Easy"
    elif wanted <= recommended:
        verdict = "Good"
    elif wanted <= stretch:
        verdict = "Tight"
    else:
        verdict = "Too high, you may stop it later"
    plan_parts = list(profile.get("plan_parts") or [])
    annual_rate = _rate(profile.get("fallback_annual_rate", DEFAULT_GOAL_RETURN_RATE))
    nearest_goal = min(
        (goal for goal in goals if goal.get("amount") is not None and goal.get("years") is not None),
        key=lambda goal: int(goal["years"]),
        default=None,
    )
    goal_need = None
    goal_chance = None
    months_needed = None
    if nearest_goal is not None:
        goal_amount = _positive(nearest_goal["amount"], "Goal amount")
        goal_years = _years(nearest_goal["years"])
        if plan_parts:
            goal_need = calculate_required_monthly_plan_sip(goal_amount, plan_parts, goal_years)
            future_value = lambda amount, month_count: calculate_plan_future_value_months(  # Grow each saved part on its own rate.
                amount,
                plan_parts,
                month_count,
            )
        else:
            goal_need = calculate_required_monthly_sip(goal_amount, annual_rate, goal_years)
            future_value = lambda amount, month_count: calculate_sip_future_value_months(  # Use the configured teaching rate without a plan.
                amount,
                annual_rate,
                month_count,
            )
        goal_chance = _money(min(HUNDRED, recommended / goal_need * HUNDRED)) if goal_need else ZERO
        if recommended > ZERO:
            months_needed = next(
                (
                    month_count
                    for month_count in range(1, 601)
                    if future_value(recommended, month_count) >= goal_amount
                ),
                None,
            )
    cushion = _round_down_hundred(available * MONTHLY_AMOUNT_SHARES["cushion"])
    invest_for_bar = invest_amount
    basics_for_bar = basics_amount
    cushion_for_bar = min(cushion, max(ZERO, available - invest_for_bar - basics_for_bar))
    free = max(ZERO, available - invest_for_bar - basics_for_bar - cushion_for_bar)
    bar_amounts = {
        "expenses": expenses,
        "emi": emis,
        "basics": basics_for_bar,
        "invest": invest_for_bar,
        "cushion": cushion_for_bar,
        "free": free,
    }
    bar_total = sum(bar_amounts.values(), ZERO)
    bar = {
        name: {
            "amount": _money(amount),
            "percent": _money(amount / bar_total * HUNDRED) if bar_total > ZERO else ZERO,
        }
        for name, amount in bar_amounts.items()
    }
    gauge_max = max(wanted, available, goal_need or ZERO, Decimal("1"))
    gauge = {
        "wanted_percent": _money(wanted / gauge_max * HUNDRED),
        "can_percent": _money(available / gauge_max * HUNDRED),
        "need_percent": _money((goal_need or ZERO) / gauge_max * HUNDRED),
    }
    step_up_percent = DEFAULT_ANNUAL_STEP_UP_PERCENT
    step_up_growth: dict[str, dict[str, Decimal]] = {}
    for years in (5, 10):
        months = years * 12
        if plan_parts:
            flat = calculate_plan_future_value_months(recommended, plan_parts, months)
            stepped = calculate_step_up_plan_future_value(
                recommended,
                plan_parts,
                months,
                "mid",
                step_up_percent,
            )
        else:
            flat = calculate_sip_future_value_months(recommended, annual_rate, months)
            stepped = calculate_step_up_sip_future_value(
                recommended,
                annual_rate,
                months,
                step_up_percent,
            )
        step_up_growth[str(years)] = {"flat": flat, "step_up": stepped}
    tips = []
    if surplus <= ZERO:
        tips = [
            "Look for one expense you can lower.",
            "Think about a safe way to raise your income.",
            "Ask your lender about restructuring debt before missing a payment.",
        ]
    elif not_ready:
        tips = [
            "Build an emergency fund or pay high-interest debt before investing.",
            "Do not borrow money just to invest.",
        ]
    plain_english = (
        f"You have Rs {_money(available):,.2f} left each month. "
        f"We suggest Rs {_money(recommended):,.2f} so you still have money for surprises."
        if surplus > ZERO
        else "There is no money left after expenses and EMI. Try the steps below before investing."
    )
    now = datetime.now(timezone.utc)
    local_time = now.astimezone(ZoneInfo("Asia/Kolkata"))
    return {
        "wanted": _money(wanted),
        "can": _money(available),
        "surplus": _money(surplus),
        "income": _money(income),
        "expenses": _money(expenses),
        "total_emi": _money(emis),
        "custom_slider_max": _round_down_hundred(available),
        "comfortable": comfortable,
        "recommended": recommended,
        "stretch": stretch,
        "invest": invest_amount,
        "basics": basics_amount,
        "cushion": cushion_for_bar,
        "free": free,
        "verdict": verdict,
        "income_stability": stability,
        "stability_multiplier": multiplier,
        "ready_to_invest": not not_ready and surplus > ZERO,
        "emergency_fund_gap": _money(emergency_gap),
        "emergency_fund_months_at_basics": emergency_build_months,
        "basics_priority": "high-interest debt" if high_interest_debt else "emergency fund",
        "goal": nearest_goal,
        "goal_need": _money(goal_need) if goal_need is not None else None,
        "goal_chance_at_recommended": goal_chance,
        "months_to_goal_at_recommended": months_needed,
        "annual_return_assumption": annual_rate,
        "gauge": gauge,
        "stacked_bar": bar,
        "step_up": {
            "annual_percent": step_up_percent,
            "growth": step_up_growth,
        },
        "tips": tips,
        "plain_english": plain_english,
        "calculated_at": now.isoformat().replace("+00:00", "Z"),
        "calculated_at_local": (
            f"{local_time.strftime('%d %b %Y')}, "
            f"{local_time.strftime('%I:%M %p').lstrip('0')}"
        ),
    }


def _goal_date(value: object, label: str) -> date:
    """Convert one goal calendar date without involving browser or float math."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        date_text = str(value)[:10]
        if len(date_text) == 7:
            date_text += "-01"
        return date.fromisoformat(date_text)
    except (TypeError, ValueError):
        raise ValueError(f"Please enter a valid {label} date.")


def _goal_datetime(value: object) -> datetime | None:
    """Read an optional stored timestamp so snapshots can be compared with log times."""
    if isinstance(value, datetime):
        parsed = value
    elif value is None:
        return None
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _goal_month_index(value: date) -> int:
    """Turn a calendar month into an integer that can be compared exactly."""
    return value.year * 12 + value.month - 1


def _goal_periods(start_month: object, as_of: date) -> int:
    """Count inclusive start-of-month growth periods from a log to today."""
    start = _goal_date(start_month, "investment month")
    return max(0, _goal_month_index(as_of) - _goal_month_index(start) + 1)


def _goal_monthly_mix(parts: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Keep the saved plan's separate part weights and middle return rates."""
    result = []
    for part in parts:
        share = _non_negative(part.get("share", 0), "Part share")
        if share == ZERO:
            continue
        rate = _rate(part.get("expected_return_mid", part.get("mid_rate", 0)))
        result.append({
            "idea_id": str(part.get("idea_id", "")),
            "share": share,
            "rate": rate,
        })
    if result and sum((part["share"] for part in result), ZERO) != HUNDRED:
        raise ValueError("Saved plan part shares must add up to 100%.")
    return result


def _goal_part_allocations(amount: Decimal, mix: Sequence[Mapping[str, object]]) -> list[Decimal]:
    """Split one amount by saved plan weights while preserving every paise."""
    if not mix:
        return [amount]
    return split_monthly_amount(amount, [part["share"] for part in mix])


def _goal_lump_value(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """Grow one part's contribution from the start of its month to the value date."""
    if amount == ZERO or months <= 0 or annual_rate == ZERO:
        return amount
    monthly_rate = annual_rate / Decimal("12") / HUNDRED
    return amount * ((Decimal("1") + monthly_rate) ** months)


def _goal_sip_value(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """Use the same start-of-month SIP formula for one plan part."""
    if months <= 0:
        return ZERO
    if annual_rate == ZERO:
        return amount * Decimal(months)
    monthly_rate = annual_rate / Decimal("12") / HUNDRED
    factor = (
        ((Decimal("1") + monthly_rate) ** months - Decimal("1"))
        / monthly_rate
        * (Decimal("1") + monthly_rate)
    )
    return amount * factor


def calculate_goal_investment_progress(
    goal_amount: object,
    goal_years: object,
    start_date: object,
    planned_monthly_amount: object,
    plan_parts: Sequence[Mapping[str, object]],
    logs: Sequence[Mapping[str, object]],
    value_snapshot: Mapping[str, object] | None = None,
    as_of_date: object | None = None,
) -> dict[str, object]:
    """Calculate goal progress from real logs and each plan part's own return assumption."""
    target = _positive(goal_amount, "Goal amount")
    years = _years(goal_years)
    start = _goal_date(start_date, "goal start")
    as_of = _goal_date(as_of_date or date.today(), "progress")
    planned = _non_negative(planned_monthly_amount, "Planned monthly amount")
    if start > as_of:
        raise ValueError("Goal start date cannot be in the future.")

    mix = _goal_monthly_mix(plan_parts)
    if not mix:
        mix = [{"idea_id": "", "share": HUNDRED, "rate": ZERO}]
    rate_by_id = {str(part["idea_id"]): part["rate"] for part in mix}
    active_logs = [log for log in logs if log.get("deleted_at") is None]
    total_invested = sum(
        (_non_negative(log.get("amount", 0), "Logged amount") for log in active_logs),
        ZERO,
    )
    months_passed = _goal_month_index(as_of) - _goal_month_index(start) + 1
    goal_horizon = years * 12
    remaining_months = max(0, goal_horizon - months_passed)
    value_by_part = {str(part["idea_id"]): ZERO for part in mix}
    positive_months: set[str] = set()
    all_logged_months: set[str] = set()
    last_updated_values: list[datetime] = []

    for log in logs:
        updated = _goal_datetime(log.get("updated_at") or log.get("created_at"))
        if updated is not None:
            last_updated_values.append(updated)

    for log in active_logs:
        month = _goal_date(log.get("month"), "investment month")
        month_key = month.strftime("%Y-%m")
        amount = _non_negative(log.get("amount", 0), "Logged amount")
        all_logged_months.add(month_key)
        if amount > ZERO:
            positive_months.add(month_key)

    def add_part_value(part_id: str, amount: Decimal, periods: int) -> None:
        """Add one aged amount to its own plan-part bucket."""
        key = part_id if part_id in value_by_part else str(mix[0]["idea_id"])
        value_by_part[key] += _goal_lump_value(
            amount,
            rate_by_id.get(key, ZERO),
            periods,
        )

    snapshot_value = None
    snapshot_time = None
    if value_snapshot is not None:
        snapshot_value = _non_negative(value_snapshot.get("value", 0), "Snapshot value")
        snapshot_time = _goal_datetime(value_snapshot.get("taken_at"))
        if snapshot_time is None:
            raise ValueError("The saved value snapshot has no valid date.")
        snapshot_month = _goal_date(snapshot_time, "snapshot")
        snapshot_periods = max(
            0,
            _goal_month_index(as_of) - _goal_month_index(snapshot_month),
        )
        snapshot_allocations = _goal_part_allocations(snapshot_value, mix)
        for part, amount in zip(mix, snapshot_allocations):
            add_part_value(str(part["idea_id"]), amount, snapshot_periods)
        last_updated_values.append(snapshot_time)

    for log in active_logs:
        created = _goal_datetime(log.get("created_at"))
        if snapshot_time is not None and (created is None or created <= snapshot_time):
            continue
        amount = _non_negative(log.get("amount", 0), "Logged amount")
        periods = _goal_periods(log.get("month"), as_of)
        part_id = str(log.get("part_id") or "")
        if part_id in value_by_part:
            add_part_value(part_id, amount, periods)
        else:
            allocations = _goal_part_allocations(amount, mix)
            for part, part_amount in zip(mix, allocations):
                add_part_value(str(part["idea_id"]), part_amount, periods)

    value_today = sum(value_by_part.values(), ZERO)
    planned_parts = _goal_part_allocations(planned, mix)
    expected_by_now = sum(
        (
            _goal_sip_value(amount, part["rate"], months_passed)
            for amount, part in zip(planned_parts, mix)
        ),
        ZERO,
    )
    chance_with_plan_value = sum(
        (
            _goal_sip_value(amount, part["rate"], goal_horizon)
            for amount, part in zip(planned_parts, mix)
        ),
        ZERO,
    )
    final_from_current_value = sum(
        (
            _goal_lump_value(value_by_part[str(part["idea_id"])], part["rate"], remaining_months)
            for part in mix
        ),
        ZERO,
    )
    future_planned_value = sum(
        (
            _goal_sip_value(amount, part["rate"], remaining_months)
            for amount, part in zip(planned_parts, mix)
        ),
        ZERO,
    )
    projected_final = final_from_current_value + future_planned_value
    catch_up_coefficient = sum(
        (
            part["share"] / HUNDRED
            * _goal_sip_value(Decimal("1"), part["rate"], remaining_months)
            for part in mix
        ),
        ZERO,
    )
    catch_up = (
        _money(max(ZERO, (target - final_from_current_value) / catch_up_coefficient))
        if catch_up_coefficient > ZERO
        else None
    )
    catch_up_extra = (
        _money(max(ZERO, catch_up - planned))
        if catch_up is not None
        else None
    )

    ahead_behind = value_today - expected_by_now
    ahead_behind_percent = (
        ahead_behind / expected_by_now * HUNDRED
        if expected_by_now > ZERO
        else ZERO
    )
    ahead = ahead_behind >= ZERO
    ahead_behind_amount = _money(abs(ahead_behind))
    friendly_message = (
        "Great, you are ahead!"
        if ahead
        else (
            f"You are a little behind. Invest Rs {catch_up_extra} extra next month to catch up."
            if catch_up_extra is not None and catch_up_extra > ZERO
            else "You are a little behind. Keep logging your real investments."
        )
    )
    current_month = as_of.strftime("%Y-%m")
    streak = 0
    streak_index = _goal_month_index(as_of)
    while True:
        streak_year, streak_month = divmod(streak_index, 12)
        if f"{streak_year:04d}-{streak_month + 1:02d}" not in positive_months:
            break
        streak += 1
        streak_index -= 1
    latest_update = max(last_updated_values) if last_updated_values else None

    return {
        "total_invested": _money(total_invested),
        "value_today": _money(value_today),
        "value_progress_percent": calculate_goal_chance(value_today, target),
        "value_label": "Actual (you entered)" if snapshot_value is not None else "Estimated (assumption)",
        "expected_by_now": _money(expected_by_now),
        "ahead_behind": _money(ahead_behind),
        "ahead_behind_percent": _money(ahead_behind_percent),
        "ahead_behind_direction": "ahead" if ahead else "behind",
        "ahead_behind_amount": ahead_behind_amount,
        "friendly_message": friendly_message,
        "projected_final_value": _money(projected_final),
        "chance_with_plan": calculate_goal_chance(chance_with_plan_value, target),
        "chance_with_real_investments": calculate_goal_chance(projected_final, target),
        "catch_up_monthly": catch_up,
        "catch_up_extra": catch_up_extra,
        "next_step": (
            f"To stay on track, invest Rs {catch_up} per month."
            if catch_up is not None and catch_up > planned
            else "Your planned amount is enough for the remaining months."
            if catch_up is not None
            else "Your goal date has passed. Update your goal date or target."
        ),
        "months_passed": months_passed,
        "remaining_months": remaining_months,
        "streak_months": streak,
        "consistency_percent": _money(Decimal(len(positive_months)) / Decimal(months_passed) * HUNDRED),
        "last_updated": latest_update,
        "current_month_logged": current_month in all_logged_months,
    }


def calculate_lump_sum_future_value(principal: object, annual_rate: object, years: object) -> Decimal:
    """Calculate lump-sum growth: starting money, rate and years go in; future value comes out."""
    amount = _non_negative(principal, "Lump sum")
    rate = _rate(annual_rate)
    whole_years = _years(years)
    if rate == ZERO:
        return _money(amount)
    r = rate / HUNDRED
    # The formula applies growth once for each whole year.
    result = amount * ((Decimal("1") + r) ** whole_years)
    return _money(result)


def calculate_required_monthly_sip(goal_amount: object, annual_rate: object, years: object) -> Decimal:
    """Calculate the monthly SIP needed for a goal: goal, rate and years go in; monthly SIP comes out."""
    goal = _positive(goal_amount, "Goal amount")
    rate = _rate(annual_rate)
    whole_years = _years(years)
    months = whole_years * 12
    if rate == ZERO:
        # At 0%, every rupee counted toward the goal is simply divided across the months.
        return _money(goal / Decimal(months))
    r = rate / Decimal("12") / HUNDRED
    denominator = ((Decimal("1") + r) ** months - Decimal("1")) * (Decimal("1") + r)
    result = goal * r / denominator
    return _money(result)


def calculate_inflation_adjusted_value(future_value: object, inflation_rate: object, years: object) -> Decimal:
    """Measure today's buying power of future money: future value, inflation and years go in."""
    future = _non_negative(future_value, "Future value")
    inflation = _non_negative(inflation_rate, "Inflation rate")
    if inflation > HUNDRED:
        raise ValueError("Inflation rate cannot be more than 100.")
    whole_years = _years(years)
    if inflation == ZERO:
        return _money(future)
    # Inflation reduces what future money can buy, just like shrinking buying power.
    result = future / ((Decimal("1") + inflation / HUNDRED) ** whole_years)
    return _money(result)


def calculate_money_breakdown(monthly_amount: object, annual_rate: object, years: object) -> dict[str, Decimal]:
    """Compare money invested with estimated gain: SIP inputs go in; invested and earned values come out."""
    principal = _non_negative(monthly_amount, "Monthly amount")
    whole_years = _years(years)
    months = whole_years * 12
    invested = principal * Decimal(months)
    future_value = calculate_sip_future_value(principal, annual_rate, whole_years)
    earned = max(future_value - invested, ZERO)
    return {
        "invested": _money(invested),
        "earned": _money(earned),
        "future_value": future_value,
    }


def calculate_savings_rate(income: object, expenses: object) -> Decimal:
    """Find the percentage of income left after expenses: income and expenses go in."""
    monthly_income = _positive(income, "Monthly income")
    monthly_expenses = _non_negative(expenses, "Monthly expenses")
    # Savings is what remains, and this is shown as a percentage of income.
    result = (monthly_income - monthly_expenses) / monthly_income * HUNDRED
    return _money(result)


def calculate_debt_to_income_ratio(total_monthly_emis: object, monthly_income: object) -> Decimal:
    """Find EMI percentage of income: monthly EMIs and income go in."""
    emis = _non_negative(total_monthly_emis, "Total monthly EMIs")
    income = _positive(monthly_income, "Monthly income")
    result = emis / income * HUNDRED
    return _money(result)


def calculate_emergency_fund_months(savings: object, monthly_expenses: object) -> Decimal:
    """Measure how many expense months savings can cover: savings and expenses go in."""
    fund = _non_negative(savings, "Savings")
    expenses = _non_negative(monthly_expenses, "Monthly expenses")
    if expenses == ZERO:
        return ZERO.quantize(MONEY)
    return _money(fund / expenses)


def _normalise_debt(debt: Mapping[str, object]) -> dict[str, object]:
    """Turn one debt record into exact balance, interest and EMI values."""
    balance = _non_negative(debt.get("balance", debt.get("amount", 0)), "Debt balance")
    rate_value = debt.get("interest_rate", debt.get("annual_rate", 0))
    rate = _decimal(rate_value, "Debt interest rate")
    if rate < ZERO or rate > HUNDRED:
        raise ValueError("Debt interest rate must be between 0 and 100.")
    emi = _non_negative(debt.get("emi", debt.get("monthly_emi", 0)), "Debt EMI")
    name = str(debt.get("name", "Debt"))
    return {"name": name, "balance": balance, "rate": rate, "emi": emi}


def calculate_debt_payoff(
    debts: Iterable[Mapping[str, object]],
    strategy: str = "avalanche",
    extra_monthly: object = 0,
) -> dict[str, object]:
    """Build a month-by-month debt payoff plan: debts and strategy go in; payoff details come out."""
    normalised = [_normalise_debt(debt) for debt in debts]
    active = [item for item in normalised if item["balance"] > ZERO]
    if not active:
        return {"strategy": strategy.lower(), "months": 0, "months_to_debt_free": 0,
                "total_interest_paid": ZERO.quantize(MONEY), "schedule": []}

    strategy_name = strategy.lower()
    if strategy_name not in {"avalanche", "snowball"}:
        raise ValueError("Debt strategy must be avalanche or snowball.")

    working = [
        {"name": item["name"], "balance": item["balance"], "rate": item["rate"], "emi": item["emi"]}
        for item in active
    ]
    extra_payment = _non_negative(extra_monthly, "Extra monthly debt payment")
    monthly_budget = sum((item["emi"] for item in working), ZERO) + extra_payment
    if monthly_budget <= ZERO:
        raise ValueError("At least one debt EMI must be greater than 0.")

    interest_paid = ZERO
    schedule: list[dict[str, object]] = []
    months = 0
    max_months = 1200
    while any(item["balance"] > ZERO for item in working):
        if months >= max_months:
            raise ValueError("Debt could not be repaid within 100 years; please increase the EMI.")
        months += 1
        month_paid_interest = ZERO
        remaining_budget = monthly_budget

        # Interest is calculated before that month's payment.
        for item in working:
            if item["balance"] <= ZERO:
                continue
            monthly_interest = item["balance"] * (item["rate"] / HUNDRED) / Decimal("12")
            item["balance"] = _money(item["balance"] + monthly_interest)
            interest_paid += monthly_interest
            month_paid_interest += monthly_interest

        # Make each debt's planned EMI payment before choosing one extra-payment target.
        for item in working:
            if item["balance"] <= ZERO:
                continue
            payment = min(item["emi"], item["balance"], remaining_budget)
            item["balance"] = max(item["balance"] - payment, ZERO)
            remaining_budget -= payment

        # Put leftover payment toward the chosen debt; that debt was chosen afresh each month.
        targets = [item for item in working if item["balance"] > ZERO]
        if targets and remaining_budget > ZERO:
            if strategy_name == "avalanche":
                target = max(targets, key=lambda item: item["rate"])
            else:
                target = min(targets, key=lambda item: item["balance"])
            payment = min(remaining_budget, target["balance"])
            target["balance"] = max(target["balance"] - payment, ZERO)

        schedule.append({
            "month": months,
            "interest_paid": _money(month_paid_interest),
            "balances": {item["name"]: _money(item["balance"]) for item in working},
        })

    return {
        "strategy": strategy_name,
        "months": months,
        "months_to_debt_free": months,
        "total_interest_paid": _money(interest_paid),
        "schedule": schedule,
    }


def calculate_debt_plans(debts: Iterable[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """Calculate both repayment plans: debt data goes in; avalanche and snowball come out."""
    debt_list = list(debts)
    avalanche = calculate_debt_payoff(debt_list, "avalanche")
    snowball = calculate_debt_payoff(debt_list, "snowball")
    return {
        "avalanche": avalanche,
        "snowball": snowball,
        "interest_saved": _money(
            max(avalanche["total_interest_paid"], snowball["total_interest_paid"])
            - min(avalanche["total_interest_paid"], snowball["total_interest_paid"])
        ),
    }


# Short names keep later API and chatbot tools easy to read.
calculate_sip = calculate_sip_future_value
calculate_lump_sum = calculate_lump_sum_future_value
calculate_required_sip = calculate_required_monthly_sip
calculate_inflation_adjusted = calculate_inflation_adjusted_value
calculate_money_invested_vs_earned = calculate_money_breakdown
calculate_debt_plan = calculate_debt_plans

# Plain formula names are also exported for modules written in later phases.
sip_future_value = calculate_sip_future_value
lump_sum_future_value = calculate_lump_sum_future_value
required_monthly_sip = calculate_required_monthly_sip
inflation_adjusted_value = calculate_inflation_adjusted_value
savings_rate = calculate_savings_rate
debt_to_income_ratio = calculate_debt_to_income_ratio
emergency_fund_months = calculate_emergency_fund_months
debt_payoff = calculate_debt_payoff


def calculate_investor_type(answers: Iterable[int]) -> tuple[str, int, str]:
    """Score seven 1-to-5 risk answers and return a plain-English investor type."""
    answer_list = list(answers)
    if len(answer_list) != 7:
        raise ValueError("Please answer all 7 risk questions.")
    if any(answer < 1 or answer > 5 for answer in answer_list):
        raise ValueError("Each risk answer must be between 1 and 5.")
    score = sum(answer_list)
    if score <= 14:
        investor_type = "conservative"
        explanation = "You prefer steadier choices and may feel uncomfortable with large price swings."
    elif score <= 24:
        investor_type = "balanced"
        explanation = "You accept some ups and downs and want a mix of growth and safety."
    else:
        investor_type = "aggressive"
        explanation = "You can consider more ups and downs for a chance of higher long-term growth."
    return investor_type, score, explanation


def calculate_asset_mix(investor_type: str) -> dict[str, object]:
    """Choose the starting percentage mix for one of three investor types."""
    choices = {
        "conservative": {
            "equity": 20,
            "debt": 40,
            "gold": 10,
            "fd_cash": 30,
            "range": "about 5% to 8% per year, not guaranteed",
        },
        "balanced": {
            "equity": 50,
            "debt": 30,
            "gold": 10,
            "fd_cash": 10,
            "range": "about 7% to 10% per year, not guaranteed",
        },
        "aggressive": {
            "equity": 70,
            "debt": 15,
            "gold": 10,
            "fd_cash": 5,
            "range": "about 9% to 12% per year, not guaranteed",
        },
    }
    key = investor_type.lower()
    if key not in choices:
        raise ValueError("Investor type must be conservative, balanced or aggressive.")
    item = choices[key]
    return {
        "investor_type": key,
        "equity": item["equity"],
        "debt": item["debt"],
        "gold": item["gold"],
        "fd_cash": item["fd_cash"],
        "expected_return_range": item["range"],
    }


def calculate_readiness(
    monthly_income: object,
    monthly_expenses: object,
    savings: object,
    debts: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Check emergency savings, costly debt and savings rate before investing."""
    income = _positive(monthly_income, "Monthly income")
    expenses = _non_negative(monthly_expenses, "Monthly expenses")
    fund = _non_negative(savings, "Savings")
    emergency_months = calculate_emergency_fund_months(fund, expenses)
    savings_rate_value = calculate_savings_rate(income, expenses)
    debt_list = list(debts)
    high_interest_debt = any(
        _decimal(debt.get("interest_rate", debt.get("annual_rate", 0)), "Debt interest rate") > Decimal("15")
        for debt in debt_list
    )

    checks = [
        {
            "name": "Emergency fund",
            "passed": expenses == ZERO or emergency_months >= Decimal("3"),
            "detail": (
                "No monthly expenses entered"
                if expenses == ZERO
                else f"{_money(emergency_months)} months of expenses saved"
            ),
        },
        {
            "name": "High-interest debt",
            "passed": not high_interest_debt,
            "detail": "No debt above 15% interest" if not high_interest_debt else "Debt above 15% interest found",
        },
        {
            "name": "Savings rate",
            "passed": savings_rate_value >= Decimal("20"),
            "detail": f"{_money(savings_rate_value)}% of income remains",
        },
    ]
    fix_plan: list[str] = []
    if expenses > ZERO and emergency_months < Decimal("3"):
        fix_plan.append("Build a cash emergency fund for at least 3 months of expenses.")
    if high_interest_debt:
        fix_plan.append("Pay down debt above 15% interest with an avalanche or snowball plan.")
    if savings_rate_value < Decimal("20"):
        fix_plan.append("Reduce optional spending or raise income until you keep at least 20% of income.")
    ready = not fix_plan
    return {
        "ready": ready,
        "emergency_fund_months": _money(emergency_months),
        "has_high_interest_debt": high_interest_debt,
        "savings_rate": _money(savings_rate_value),
        "checks": checks,
        "fix_plan": fix_plan,
    }


def allocation_plan(monthly_amount: object, investor_type: str) -> dict[str, object]:
    """Split a monthly amount into seven jars and show estimated 5- and 10-year growth."""
    amount = _non_negative(monthly_amount, "Monthly investment amount")
    amount = _money(amount)
    mix = calculate_asset_mix(investor_type)
    class_amounts = {
        "Equity": amount * Decimal(mix["equity"]) / HUNDRED,
        "Debt": amount * Decimal(mix["debt"]) / HUNDRED,
        "Gold": amount * Decimal(mix["gold"]) / HUNDRED,
        "Cash": amount * Decimal(mix["fd_cash"]) / HUNDRED,
    }

    # These shares divide each class into the simple investment ideas from the catalog.
    jars = [
        ("index-sip", "Index fund SIP", "Equity", Decimal("0.60"), Decimal("6"), Decimal("10"), Decimal("13")),
        ("equity-funds", "Equity mutual funds", "Equity", Decimal("0.25"), Decimal("5"), Decimal("11"), Decimal("15")),
        ("elss", "ELSS", "Equity", Decimal("0.15"), Decimal("5"), Decimal("10"), Decimal("15")),
        ("ppf", "PPF", "Debt", Decimal("0.50"), Decimal("5"), Decimal("7"), Decimal("8")),
        ("debt-fund", "Debt mutual funds", "Debt", Decimal("0.50"), Decimal("3"), Decimal("6"), Decimal("8")),
        ("gold", "Gold fund", "Gold", Decimal("1.00"), Decimal("2"), Decimal("7"), Decimal("12")),
        ("fd-rd", "FD or RD", "Cash", Decimal("1.00"), Decimal("3"), Decimal("6"), Decimal("8")),
    ]

    # Each jar gets its class share, rounded to paise before we calculate growth.
    rows = []
    for idea_id, name, asset_class, share, low, mid, high in jars:
        jar_amount = _money(class_amounts[asset_class] * share)
        growth = {}
        for years in (5, 10):
            growth[str(years)] = {
                "low": calculate_sip_future_value(jar_amount, low, years),
                "mid": calculate_sip_future_value(jar_amount, mid, years),
                "high": calculate_sip_future_value(jar_amount, high, years),
            }
        rows.append({
            "idea_id": idea_id,
            "name": name,
            "asset_class": asset_class,
            "monthly_amount": jar_amount,
            "expected_return_low": low,
            "expected_return_mid": mid,
            "expected_return_high": high,
            "growth": growth,
            "label": "Expected, not guaranteed",
        })

    # Paise left by rounding go into the largest jar, so the plan always adds up.
    difference = amount - sum((row["monthly_amount"] for row in rows), ZERO)
    if rows and difference != ZERO:
        largest = max(rows, key=lambda row: row["monthly_amount"])
        largest["monthly_amount"] += difference
        for years in (5, 10):
            largest["growth"][str(years)] = {
                "low": calculate_sip_future_value(
                    largest["monthly_amount"], largest["expected_return_low"], years
                ),
                "mid": calculate_sip_future_value(
                    largest["monthly_amount"], largest["expected_return_mid"], years
                ),
                "high": calculate_sip_future_value(
                    largest["monthly_amount"], largest["expected_return_high"], years
                ),
            }

    amount_label = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    five_year_middle = _money(sum( # Sum every five-year middle row before rounding the total.
        (row["growth"]["5"]["mid"] for row in rows), # Add the exact Decimal row values.
        ZERO, # Start the total from an exact Decimal zero.
    )) # Round only the completed five-year total to paise.
    ten_year_middle = _money(sum( # Sum every ten-year middle row before rounding the total.
        (row["growth"]["10"]["mid"] for row in rows), # Add the exact Decimal row values.
        ZERO, # Start the total from an exact Decimal zero.
    )) # Round only the completed ten-year total to paise.
    totals = { # Group the three backend totals for the API response.
        "monthly": _money(sum((row["monthly_amount"] for row in rows), ZERO)), # Sum each monthly row.
        "five_year_middle": five_year_middle, # Keep the five-year row sum.
        "ten_year_middle": ten_year_middle, # Keep the ten-year row sum.
    } # Finish the totals object.
    return {
        "monthly_amount": amount,
        "investor_type": investor_type.lower(),
        "items": rows,
        "total": sum((row["monthly_amount"] for row in rows), ZERO),
        "totals": totals, # Send the Decimal totals to the API response.
        "summary": f"Your ₹{amount_label} each month, split into 7 jars.",
        "label": "Expected, not guaranteed",
    }


def calculate_health_score(
    monthly_income: object,
    monthly_expenses: object,
    savings: object,
    debts: Iterable[Mapping[str, object]],
    goals: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Score savings, emergency money, monthly debt and goal progress out of 100."""
    income = _positive(monthly_income, "Monthly income")
    expenses = _non_negative(monthly_expenses, "Monthly expenses")
    savings_amount = _non_negative(savings, "Savings")
    debt_list = list(debts)
    goal_list = list(goals)

    # Each part has a fixed maximum so the score is easy to understand.
    save_percent = calculate_savings_rate(income, expenses)
    savings_points = max(ZERO, min(Decimal("30"), save_percent * Decimal("1.5")))
    emergency_months = calculate_emergency_fund_months(savings_amount, expenses)
    emergency_points = (
        Decimal("25")
        if expenses == ZERO
        else min(Decimal("25"), emergency_months / Decimal("3") * Decimal("25"))
    )
    monthly_emis = sum(
        (_non_negative(debt.get("emi", 0), "Debt EMI") for debt in debt_list),
        ZERO,
    )
    debt_ratio = calculate_debt_to_income_ratio(monthly_emis, income)
    debt_points = max(ZERO, Decimal("25") * (Decimal("1") - debt_ratio / HUNDRED))

    # If there are goals, compare saved money with each target and average the progress.
    goal_progress = []
    if goal_list:
        progress_values = []
        for goal in goal_list:
            target = _positive(goal.get("amount", 0), "Goal amount")
            progress = min(Decimal("1"), savings_amount / target)
            progress_values.append(progress)
            goal_progress.append({
                "name": str(goal.get("name", "Goal")),
                "amount": _money(target),
                "years": int(goal.get("years", 1)),
                "progress_percent": _money(progress * HUNDRED),
            })
        goal_points = sum(progress_values, ZERO) / Decimal(len(progress_values)) * Decimal("20")
    else:
        goal_points = ZERO

    factors = {
        "savings": _money(savings_points),
        "emergency_fund": _money(emergency_points),
        "debt": _money(debt_points),
        "goals": _money(goal_points),
    }
    score = int(sum(factors.values(), ZERO).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hurting = sorted(factors.items(), key=lambda item: item[1])[:2]
    hurt_labels = {
        "savings": "Your savings rate needs attention.",
        "emergency_fund": "Your emergency fund needs attention.",
        "debt": "Your debt payments need attention.",
        "goals": "Your goal savings need attention.",
    }
    return {
        "score": max(0, min(100, score)),
        "factors": factors,
        "top_hurts": [
            hurt_labels[name]
            for name, points in hurting
            if points < (Decimal("20") if name == "savings" else Decimal("15"))
        ],
        "emergency_fund_months": emergency_months,
        "monthly_left": income - expenses,
        "suggested_monthly_amount": max(ZERO, income - expenses),
        "debt_to_income_ratio": debt_ratio,
        "goal_progress": factors["goals"],
        "goals": goal_progress,
    }
