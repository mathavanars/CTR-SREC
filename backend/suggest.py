"""Build a sourced, goal-aware suggestion without claiming to predict markets."""

from decimal import Decimal
from typing import Any, Mapping

from backend.calculators import (
    HUNDRED,
    ZERO,
    _money,
    calculate_sip_future_value,
    calculate_smart_mix,
    calculate_stress_test,
    max_parts,
    normalize_shares,
    split_monthly_amount,
)
from backend.market_data import market_summary
from backend.suggestion_config import (
    ASSET_RISK,
    EQUITY_RISK_PREMIUM,
    RISK_RANGES,
    SCENARIO_OFFSETS,
)


MINIMUM_PART = Decimal("500")
MINIMUM_SHARE = Decimal("10")
EQUITY_IDEAS = ("index-sip", "equity-funds", "elss")
DEBT_IDEAS = ("ppf", "debt-fund")


def _decimal(value: object) -> Decimal:
    """Convert one trusted plan value to Decimal without adding float noise."""
    return Decimal(str(value))


def _metric(snapshot: Mapping[str, Any], name: str) -> Decimal:
    """Read one validated snapshot value as an exact Decimal."""
    return _decimal(snapshot["metrics"][name]["value"])


def _nearest_goal_years(goals: list[Mapping[str, Any]]) -> int | None:
    """Return the shortest saved goal timeline, when the user has a goal."""
    if not goals:
        return None
    return min(int(goal["years"]) for goal in goals)


def _minimum_part(monthly_amount: Decimal) -> Decimal:
    """Require each part to be at least ₹500 and at least ten percent."""
    return max(MINIMUM_PART, monthly_amount * MINIMUM_SHARE / HUNDRED)


def _market_rates(snapshot: Mapping[str, Any], idea_id: str) -> dict[str, Decimal]:
    """Calculate low, expected and high rates from sourced market values."""
    standard_offset = Decimal(str(SCENARIO_OFFSETS["standard"]))
    if idea_id in {"emergency-fund", "debt-payoff"}:
        return {"low": ZERO, "mid": ZERO, "high": ZERO}
    if idea_id == "fd-rd":
        middle = _metric(snapshot, "sbi_1y_fd_rate")
        low = max(ZERO, middle - standard_offset)
        high = middle + standard_offset
    elif idea_id == "ppf":
        middle = _metric(snapshot, "ppf_rate")
        low = max(ZERO, middle - standard_offset)
        high = middle + standard_offset
    elif idea_id == "debt-fund":
        middle = _metric(snapshot, "government_10y_yield")
        low = max(ZERO, middle - standard_offset)
        high = middle + standard_offset
    elif idea_id == "gold":
        middle = _metric(snapshot, "cpi_inflation") + Decimal("1.5")
        low = max(ZERO, middle - standard_offset)
        high = middle + standard_offset
    elif idea_id in EQUITY_IDEAS:
        middle = _metric(snapshot, "government_10y_yield") + Decimal(str(EQUITY_RISK_PREMIUM))
        low = max(ZERO, middle - Decimal(str(SCENARIO_OFFSETS["equity_low"])))
        high = middle + Decimal(str(SCENARIO_OFFSETS["equity_high"]))
    else:
        middle = _metric(snapshot, "sbi_1y_fd_rate")
        low = max(ZERO, middle - standard_offset)
        high = middle + standard_offset
    return {"low": low, "mid": middle, "high": high}


def _growth_examples(
    monthly_amount: Decimal,
    rates: Mapping[str, Decimal],
) -> dict[str, dict[str, Decimal]]:
    """Calculate all three SIP scenarios for five and ten years."""
    examples = {}
    for years in (5, 10):
        invested = _money(monthly_amount * Decimal(years * 12))
        values = {
            level: calculate_sip_future_value(monthly_amount, rate, years)
            for level, rate in rates.items()
        }
        examples[str(years)] = {
            "invested": invested,
            **values,
            "earned_low": _money(values["low"] - invested),
            "earned_mid": _money(values["mid"] - invested),
            "earned_high": _money(values["high"] - invested),
        }
    return examples


def _round_class_amounts(
    monthly_amount: Decimal,
    mix: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    """Split the exact amount into asset groups and put rounding paise on the largest."""
    amounts = {
        asset: _money(monthly_amount * percentage / HUNDRED)
        for asset, percentage in mix.items()
    }
    difference = _money(monthly_amount - sum(amounts.values(), ZERO))
    if difference:
        largest = max(amounts, key=amounts.__getitem__)
        amounts[largest] += difference
    return amounts


def _merge_small_asset_groups(
    monthly_amount: Decimal,
    amounts: dict[str, Decimal],
    minimum: Decimal,
) -> tuple[dict[str, Decimal], list[str]]:
    """Move too-small class amounts into a safer usable group instead of tiny parts."""
    notes: list[str] = []
    if monthly_amount < MINIMUM_PART:
        raise ValueError("A monthly plan needs at least ₹500 so every part can meet the starting minimum.")
    if monthly_amount < Decimal("1000"):
        safest = "cash" if amounts.get("cash", ZERO) >= minimum else "debt"
        amounts = {asset: ZERO for asset in amounts}
        amounts[safest] = monthly_amount
        notes.append("A small amount uses one safe part so it can meet the ₹500 minimum.")
        return amounts, notes
    receivers = ("debt", "cash", "equity", "gold")
    for asset in ("equity", "gold", "cash", "debt"):
        if ZERO < amounts.get(asset, ZERO) < minimum:
            receiver = next(
                (
                    candidate for candidate in receivers
                    if candidate != asset and amounts.get(candidate, ZERO) >= minimum
                ),
                None,
            )
            if receiver is None:
                receiver = max(
                    (candidate for candidate in amounts if candidate != asset),
                    key=amounts.__getitem__,
                    default=asset,
                )
            amounts[receiver] += amounts[asset]
            notes.append(
                f"The {asset} amount was merged into {receiver} to keep every part at or above "
                f"{minimum:.2f} rupees."
            )
            amounts[asset] = ZERO
    return amounts, notes


def _idea_options(asset: str, monthly_amount: Decimal, tax_saving_80c: bool) -> tuple[str, ...]:
    """Choose simple products that fit the asset group and tax answer."""
    if asset == "equity":
        if tax_saving_80c and monthly_amount >= Decimal("8000"):
            return EQUITY_IDEAS
        if tax_saving_80c:
            return ("index-sip", "elss")
        return ("index-sip", "equity-funds")
    if asset == "debt":
        return DEBT_IDEAS
    if asset == "gold":
        return ("gold",)
    if asset == "cash":
        return ("fd-rd",)
    return ("fd-rd",)


def _split_asset_groups(
    amounts: Mapping[str, Decimal],
    monthly_amount: Decimal,
    tax_saving_80c: bool,
    part_limit: int,
    minimum: Decimal,
) -> list[tuple[str, str, Decimal]]:
    """Add extra products only when every resulting part still meets both minimums."""
    group_amounts = {
        asset: value for asset, value in amounts.items() if value > ZERO
    }
    counts = {asset: 1 for asset in group_amounts}
    options = {
        asset: _idea_options(asset, monthly_amount, tax_saving_80c)
        for asset in group_amounts
    }
    while sum(counts.values()) < part_limit:
        can_split = [
            asset for asset in group_amounts
            if counts[asset] < len(options[asset])
            and group_amounts[asset] / Decimal(counts[asset] + 1) >= minimum
        ]
        if not can_split:
            break
        chosen = max(can_split, key=group_amounts.__getitem__)
        counts[chosen] += 1
    parts = []
    for asset, class_amount in group_amounts.items():
        count = counts[asset]
        selected = options[asset][:count]
        equal_amount = _money(class_amount / Decimal(count))
        for idea_id in selected[:-1]:
            parts.append((asset, idea_id, equal_amount))
        parts.append((
            asset,
            selected[-1],
            _money(class_amount - equal_amount * Decimal(count - 1)),
        ))
    return parts


def _scenario_totals(parts: list[dict[str, Any]]) -> dict[str, dict[str, Decimal]]:
    """Add every part's separately calculated outcomes for each horizon and case."""
    totals: dict[str, dict[str, Decimal]] = {}
    for years in ("5", "10"):
        invested = _money(sum(
            (part["growth"][years]["invested"] for part in parts),
            ZERO,
        ))
        result = {"invested": invested}
        for level in ("low", "mid", "high"):
            result[level] = _money(sum(
                (part["growth"][years][level] for part in parts),
                ZERO,
            ))
            result[f"earned_{level}"] = _money(result[level] - invested)
        totals[years] = result
    return totals


def build_smart_suggestion(
    monthly_amount: object,
    investor_type: str,
    goals: list[Mapping[str, Any]],
    readiness: Mapping[str, Any],
    market_snapshot: Mapping[str, Any],
    tax_saving_80c: bool = False,
) -> dict[str, Any]:
    """Create exact rupee parts, three sourced scenarios and a plain-English reason."""
    amount = _money(_decimal(monthly_amount))
    if amount < ZERO:
        raise ValueError("Monthly amount cannot be negative.")
    limit = max_parts(amount)
    nearest_years = _nearest_goal_years(goals)
    minimum = _minimum_part(amount)
    basic_jar_ids: list[str] = []
    if not bool(readiness.get("ready", False)):
        if Decimal(str(readiness.get("emergency_fund_months", "0"))) < Decimal("3"):
            basic_jar_ids.append("emergency-fund")
        if bool(readiness.get("has_high_interest_debt", False)):
            basic_jar_ids.append("debt-payoff")
        if not basic_jar_ids:
            basic_jar_ids.append("emergency-fund")
        if amount < MINIMUM_PART:
            raise ValueError("A monthly plan needs at least ₹500 so every part can meet the starting minimum.")
        if amount < Decimal("1000") and len(basic_jar_ids) > 1:
            basic_jar_ids = ["debt-payoff" if "debt-payoff" in basic_jar_ids else basic_jar_ids[0]]
    goal_jar = nearest_years is not None and nearest_years < 3 and not basic_jar_ids
    mix_result = calculate_smart_mix(investor_type, market_snapshot, nearest_years)
    merge_notes: list[str] = []
    if basic_jar_ids:
        if len(basic_jar_ids) > limit:
            basic_jar_ids = basic_jar_ids[:limit]
        raw_parts = [
            ("basics", idea_id, _money(amount / Decimal(len(basic_jar_ids))))
            for idea_id in basic_jar_ids[:-1]
        ]
        last_amount = _money(amount - sum((item[2] for item in raw_parts), ZERO))
        raw_parts.append(("basics", basic_jar_ids[-1], last_amount))
        if any(item[2] < minimum for item in raw_parts):
            raw_parts = [("basics", basic_jar_ids[0], amount)]
            merge_notes.append("The basics jars were combined so the only part meets the starting minimum.")
    elif goal_jar:
        raw_parts = [("cash", "fd-rd", amount)]
        merge_notes.append("Your nearest goal is under 3 years away, so the amount stays in one safer goal jar.")
    else:
        class_amounts = _round_class_amounts(amount, mix_result["mix"])
        class_amounts, merge_notes = _merge_small_asset_groups(amount, class_amounts, minimum)
        raw_parts = _split_asset_groups(
            class_amounts,
            amount,
            tax_saving_80c,
            limit,
            minimum,
        )
    raw_amounts = [item[2] for item in raw_parts]
    shares = normalize_shares([
        _money(part_amount * HUNDRED / amount)
        for part_amount in raw_amounts
    ])
    exact_amounts = split_monthly_amount(amount, shares)
    parts: list[dict[str, Any]] = []
    for (asset, idea_id, _), share, part_amount in zip(raw_parts, shares, exact_amounts):
        rates = _market_rates(market_snapshot, idea_id)
        parts.append({
            "idea_id": idea_id,
            "asset_class": asset,
            "share": share,
            "monthly_amount": part_amount,
            "expected_return_low": rates["low"],
            "expected_return_mid": rates["mid"],
            "expected_return_high": rates["high"],
            "growth": _growth_examples(part_amount, rates),
        })
    if any(part["monthly_amount"] < minimum or part["share"] < MINIMUM_SHARE for part in parts):
        raise ValueError("This amount cannot support the minimum for every suggested part.")
    catalog_names = {
        "index-sip": "Index fund SIP",
        "equity-funds": "Equity mutual funds",
        "elss": "ELSS tax-saving fund",
        "ppf": "Public Provident Fund",
        "debt-fund": "Debt mutual fund",
        "gold": "Gold fund",
        "fd-rd": "FD or RD",
        "emergency-fund": "Emergency fund",
        "debt-payoff": "Pay off high-interest debt",
    }
    for part in parts:
        part["name"] = catalog_names[part["idea_id"]]
    scenario_totals = _scenario_totals(parts)
    stress_test = calculate_stress_test(amount, parts)
    plan_mix = {
        asset: sum(
            (part["share"] for part in parts if part["asset_class"] == asset),
            ZERO,
        )
        for asset in {part["asset_class"] for part in parts}
    }
    weighted_risk = sum(
        (
            part["share"] * Decimal(str(ASSET_RISK.get(part["asset_class"], 1.0)))
            for part in parts
        ),
        ZERO,
    ) / HUNDRED
    risk_low, risk_high = (
        Decimal(str(value)) for value in RISK_RANGES[investor_type.lower()]
    )
    mix_exception = not basic_jar_ids and not (risk_low <= weighted_risk <= risk_high)
    if goal_jar:
        reason = "The nearest goal is under 3 years away, so one safer goal jar is used."
    elif basic_jar_ids:
        reason = "The emergency fund or high-interest debt needs attention first, so investing parts are paused."
    elif len(parts) < limit:
        reason = (
            f"We use {len(parts)} parts, not {limit}, because every part must be at least "
            f"₹500 and at least 10% of the monthly amount."
        )
    else:
        reason = f"We use {len(parts)} parts because that is the limit for this monthly amount."
    sources = []
    seen_urls = set()
    for name, entry in market_snapshot["metrics"].items():
        url = entry["source_url"]
        if url not in seen_urls:
            seen_urls.add(url)
            sources.append({"name": name.replace("_", " "), "url": url})
    tilts = []
    if mix_result["goal_adjustment"]:
        tilts.append(mix_result["goal_adjustment"])
    tilts.extend(mix_result["tilts"])
    tilts.extend(merge_notes)
    if mix_exception:
        tilts.append(
            "The goal limit or minimum-part rule takes priority; the resulting risk score "
            "is outside the usual investor band."
        )
    return {
        "monthly_amount": amount,
        "investor_type": investor_type.lower(),
        "parts": parts,
        "max_parts": limit,
        "part_count": len(parts),
        "weighted_risk": weighted_risk,
        "risk_range": mix_result["risk_range"],
        "risk_band_exception": mix_exception,
        "mix": mix_result["mix"],
        "plan_mix": plan_mix,
        "tilts": tilts,
        "scenario_totals": scenario_totals,
        "stress_test": stress_test,
        "market_snapshot": market_snapshot,
        "why_this_plan": {
            "market_summary": market_summary(market_snapshot),
            "data_as_of": market_snapshot.get("data_as_of", "unknown"),
            "sources": sources,
            "means_for_you": (
                f"This plan starts with the {investor_type.title()} mix, then uses your goal time "
                "and the checked market figures. It does not predict market prices."
            ),
            "part_count_reason": reason,
            "changes_from_standard_mix": tilts,
            "disclaimer": "This is not a prediction. It shows possible outcomes.",
            "review_reminder": "Review your plan every 6 months.",
            "market_notice": market_snapshot.get("message", ""),
        },
        "tax_saving_80c": bool(tax_saving_80c),
        "label": "Assumptions, not guarantees.",
    }
