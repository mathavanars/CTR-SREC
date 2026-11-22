"""Test the exact answers and validation rules for ArthMitra calculations."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from backend.calculators import (
    calculate_sip_future_value,
    calculate_lump_sum_future_value,
    calculate_required_monthly_sip,
    calculate_inflation_adjusted_value,
    calculate_money_breakdown,
    calculate_savings_rate,
    calculate_debt_to_income_ratio,
    calculate_emergency_fund_months,
    calculate_debt_plans,
    calculate_investor_type,
    calculate_asset_mix,
    calculate_readiness,
    calculate_health_score,
    calculate_plan_growth,
    calculate_goal_investment_progress,
    max_parts,
    normalize_shares,
    split_monthly_amount,
)


def test_sip_known_answer() -> None:
    """A 5000 monthly SIP for 10 years at 12% gives the known future value."""
    result = calculate_sip_future_value("5000", "12", "10")
    assert abs(result - Decimal("1161695.38")) <= Decimal("1")
    breakdown = calculate_money_breakdown("5000", "12", "10")
    assert abs(breakdown["invested"] - Decimal("600000")) <= Decimal("1")


def test_report_sip_examples_match_the_saved_calculators() -> None:
    """Keep the report's required monthly amount and SIP examples exact."""
    assert calculate_required_monthly_sip("800000", "12", 3) == Decimal("18387.57")
    assert calculate_sip_future_value("6000", "12", 3) == Decimal("261045.88")
    assert calculate_sip_future_value("6000", "12", 5) == Decimal("494918.20")


def test_goal_log_progress_matches_six_month_sip_value() -> None:
    """Six real 6000 deposits at 12% grow with start-of-month timing."""
    plan_parts = [{
        "idea_id": "index-sip",
        "share": "100",
        "expected_return_mid": "12",
    }]
    logs = [
        {
            "amount": "6000",
            "month": date(2026, month, 1),
            "part_id": "index-sip",
            "created_at": datetime(2026, month, 2, tzinfo=timezone.utc),
            "updated_at": datetime(2026, month, 2, tzinfo=timezone.utc),
            "deleted_at": None,
        }
        for month in range(1, 7)
    ]

    result = calculate_goal_investment_progress(
        "1000000",
        5,
        date(2026, 1, 1),
        "6000",
        plan_parts,
        logs,
        as_of_date=date(2026, 6, 30),
    )

    assert result["total_invested"] == Decimal("36000.00")
    assert abs(result["value_today"] - Decimal("37281.21")) <= Decimal("1")
    assert result["value_label"] == "Estimated (assumption)"


def test_goal_snapshot_is_the_base_and_only_later_logs_are_added() -> None:
    """A real snapshot replaces estimates for older deposits and grows later entries."""
    plan_parts = [{"idea_id": "index-sip", "share": "100", "expected_return_mid": "12"}]
    logs = [
        {
            "amount": "9000",
            "month": date(2026, 1, 1),
            "part_id": "index-sip",
            "created_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
            "deleted_at": None,
        },
        {
            "amount": "6000",
            "month": date(2026, 2, 1),
            "part_id": "index-sip",
            "created_at": datetime(2026, 2, 3, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 2, 3, tzinfo=timezone.utc),
            "deleted_at": None,
        },
    ]

    result = calculate_goal_investment_progress(
        "1000000",
        5,
        date(2026, 1, 1),
        "6000",
        plan_parts,
        logs,
        {"value": "40000", "taken_at": datetime(2026, 1, 15, tzinfo=timezone.utc)},
        as_of_date=date(2026, 6, 30),
    )

    assert result["total_invested"] == Decimal("15000.00")
    assert result["value_today"] == Decimal("48346.46")
    assert result["value_label"] == "Actual (you entered)"


def test_goal_log_progress_matches_sixty_month_plan_and_skips() -> None:
    """A complete five-year log matches SIP maths and a zero month lowers consistency."""
    plan_parts = [{
        "idea_id": "index-sip",
        "share": "100",
        "expected_return_mid": "12",
    }]
    logs = []
    for offset in range(60):
        month_index = 2021 * 12 + 11 + offset
        year, month = divmod(month_index, 12)
        logs.append({
            "amount": "6000",
            "month": date(year, month + 1, 1),
            "part_id": "index-sip",
            "created_at": datetime(year, month + 1, 2, tzinfo=timezone.utc),
            "updated_at": datetime(year, month + 1, 2, tzinfo=timezone.utc),
            "deleted_at": None,
        })

    full_result = calculate_goal_investment_progress(
        "1000000",
        5,
        date(2021, 12, 1),
        "6000",
        plan_parts,
        logs,
        as_of_date=date(2026, 11, 22),
    )

    assert full_result["total_invested"] == Decimal("360000.00")
    assert abs(full_result["value_today"] - Decimal("494918.20")) <= Decimal("1")
    assert abs(full_result["projected_final_value"] - Decimal("494918.20")) <= Decimal("1")
    assert full_result["chance_with_real_investments"] == Decimal("49.49")

    skipped_logs = [dict(log) for log in logs]
    skipped_logs[-1]["amount"] = "0"
    skipped_result = calculate_goal_investment_progress(
        "1000000",
        5,
        date(2021, 12, 1),
        "6000",
        plan_parts,
        skipped_logs,
        as_of_date=date(2026, 11, 22),
    )

    assert skipped_result["total_invested"] == Decimal("354000.00")
    assert skipped_result["current_month_logged"] is True
    assert skipped_result["consistency_percent"] == Decimal("98.33")


def test_goal_catch_up_amount_reaches_the_target() -> None:
    """Using the calculated monthly catch-up amount reaches the goal within one rupee."""
    plan_parts = [{"idea_id": "index-sip", "share": "100", "expected_return_mid": "12"}]
    inputs = {
        "goal_amount": "100000",
        "goal_years": 5,
        "start_date": date(2026, 1, 1),
        "planned_monthly_amount": "1000",
        "plan_parts": plan_parts,
        "logs": [],
        "as_of_date": date(2026, 6, 30),
    }

    first_result = calculate_goal_investment_progress(**inputs)
    catch_up_result = calculate_goal_investment_progress(
        **{**inputs, "planned_monthly_amount": first_result["catch_up_monthly"]}
    )

    assert abs(catch_up_result["projected_final_value"] - Decimal("100000")) <= Decimal("1")


def test_lump_sum_known_answer() -> None:
    """One lakh growing for 10 years at 12% gives the known result."""
    result = calculate_lump_sum_future_value("100000", "12", "10")
    assert abs(result - Decimal("310584.82")) <= Decimal("1")


def test_required_monthly_sip_known_answer() -> None:
    """A ten lakh goal in five years at 12% needs about twelve thousand monthly."""
    result = calculate_required_monthly_sip("1000000", "12", "5")
    assert abs(result - Decimal("12123")) <= Decimal("1")


def test_zero_percent_sip() -> None:
    """A 0% SIP is monthly amount multiplied by the number of months."""
    assert calculate_sip_future_value("5000", "0", "10") == Decimal("600000.00")


def test_plan_part_limits_and_exact_splits() -> None:
    """Part caps follow the monthly bands and rounded splits keep the exact amount."""
    assert max_parts("6000") == 5
    assert max_parts("800") == 2
    assert max_parts("2000") == 3
    assert max_parts("6000") == 5
    assert max_parts("10000") == 7
    assert max_parts("1200") == 3
    assert max_parts("400") == 2
    for amount in ("500", "1234.56", "6000", "25000"):
        for count in (3, 5, 7):
            shares = normalize_shares([1] * count)
            pieces = split_monthly_amount(amount, shares)
            assert sum(pieces, Decimal("0")) == Decimal(amount).quantize(Decimal("0.01"))


@pytest.mark.parametrize("shares", [["90"], ["110"]])
def test_plan_split_rejects_non_100_percent_shares(shares) -> None:
    """A plan cannot be saved when its parts total 90% or 110%."""
    with pytest.raises(ValueError, match="exactly 100%"):
        split_monthly_amount("6000", shares)


def test_plan_growth_adds_part_specific_returns() -> None:
    """The 12% and 6% SIPs are calculated separately before their values are added."""
    result = calculate_plan_growth([
        {
            "monthly_amount": "3000",
            "expected_return_low": "12",
            "expected_return_mid": "12",
            "expected_return_high": "12",
        },
        {
            "monthly_amount": "3000",
            "expected_return_low": "6",
            "expected_return_mid": "6",
            "expected_return_high": "6",
        },
    ], 10)
    assert calculate_sip_future_value("3000", "12", 10) == Decimal("697017.23")
    assert calculate_sip_future_value("3000", "6", 10) == Decimal("494096.23")
    assert result["mid"] == Decimal("1191113.46")


def test_inflation_adjusted_value() -> None:
    """Inflation lowers future buying power by the inflation formula."""
    result = calculate_inflation_adjusted_value("1161695.38", "6", "10")
    assert result == Decimal("648684.63")


def test_health_calculations_handle_zero_and_normal_values() -> None:
    """Small health calculations work for normal and empty cases."""
    assert calculate_savings_rate("30000", "20000") == Decimal("33.33")
    assert calculate_debt_to_income_ratio("3000", "30000") == Decimal("10.00")
    assert calculate_emergency_fund_months("60000", "20000") == Decimal("3.00")
    assert calculate_emergency_fund_months("0", "20000") == Decimal("0.00")
    assert calculate_emergency_fund_months("60000", "0") == Decimal("0.00")


def test_debt_payoff_returns_both_plans() -> None:
    """The debt planner gives month, interest and interest-saved information."""
    debts = [
        {"name": "Loan A", "balance": "200000", "interest_rate": "12", "emi": "5000"},
        {"name": "Card", "balance": "50000", "interest_rate": "24", "emi": "3000"},
    ]
    plans = calculate_debt_plans(debt for debt in debts)
    assert plans["avalanche"]["months_to_debt_free"] > 0
    assert plans["snowball"]["months_to_debt_free"] > 0
    assert plans["avalanche"]["total_interest_paid"] >= Decimal("0.00")
    assert "interest_saved" in plans


@pytest.mark.parametrize(
    ("function", "arguments", "message"),
    [
        (calculate_sip_future_value, ("-1", "12", "10"), "cannot be negative"),
        (calculate_lump_sum_future_value, ("100", "41", "10"), "between 0 and 40"),
        (calculate_sip_future_value, ("100", "12", "51"), "between 1 and 50"),
        (calculate_savings_rate, ("0", "100"), "greater than 0"),
    ],
)
def test_friendly_validation(function, arguments, message) -> None:
    """Wrong inputs return a simple, friendly validation message."""
    with pytest.raises(ValueError, match=message):
        function(*arguments)


def test_risk_quiz_types() -> None:
    """The quiz separates conservative, balanced and aggressive answers."""
    assert calculate_investor_type([1] * 7)[0] == "conservative"
    assert calculate_investor_type([3] * 7)[0] == "balanced"
    assert calculate_investor_type([5] * 7)[0] == "aggressive"


def test_asset_mix_exact_starting_values() -> None:
    """The three starting mixes use the requested percentages."""
    conservative = calculate_asset_mix("conservative")
    balanced = calculate_asset_mix("balanced")
    aggressive = calculate_asset_mix("aggressive")
    assert (conservative["equity"], conservative["debt"], conservative["gold"], conservative["fd_cash"]) == (20, 40, 10, 30)
    assert (balanced["equity"], balanced["debt"], balanced["gold"], balanced["fd_cash"]) == (50, 30, 10, 10)
    assert (aggressive["equity"], aggressive["debt"], aggressive["gold"], aggressive["fd_cash"]) == (70, 15, 10, 5)


def test_readiness_checks_basics() -> None:
    """The readiness check finds debt, emergency and savings problems."""
    ready = calculate_readiness("30000", "20000", "60000", [])
    not_ready = calculate_readiness(
        "30000",
        "25000",
        "10000",
        [{"interest_rate": "18", "emi": "500"}],
    )
    assert ready["ready"] is True
    assert not_ready["ready"] is False
    assert not_ready["has_high_interest_debt"] is True
    assert len(not_ready["fix_plan"]) == 3


def test_health_score_and_zero_expense_edge_case() -> None:
    """Health scoring handles an empty expense list and keeps goal progress clear."""
    result = calculate_health_score(
        "30000",
        "0",
        "5000",
        [],
        [{"name": "Trip", "amount": "10000", "years": 2}],
    )
    assert 0 <= result["score"] <= 100
    assert result["goals"][0]["progress_percent"] == Decimal("50.00")
    readiness = calculate_readiness("30000", "0", "5000", [])
    assert readiness["ready"] is True
