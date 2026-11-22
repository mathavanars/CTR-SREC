"""Check investment idea facts, match rules and exact plan totals."""

from decimal import Decimal

import pytest

from backend.calculators import allocation_plan, calculate_sip_future_value
from backend.investment_ideas import (
    REQUIRED_IDEA_FIELDS,
    ideas_for_user,
    load_investment_ideas,
    match_score,
)


def test_catalog_has_all_fields_and_sensible_return_ranges() -> None:
    """Every listed idea has its teaching facts and ordered return assumptions."""
    ideas = load_investment_ideas()
    assert len(ideas) >= 8
    for idea in ideas:
        assert REQUIRED_IDEA_FIELDS <= idea.keys()
        assert 1 <= idea["risk_level"] <= 5
        assert idea["expected_return_low"] <= idea["expected_return_mid"]
        assert idea["expected_return_mid"] <= idea["expected_return_high"]
        assert len(idea["quiz"]) == 2
        assert all(len(question["options"]) == 3 for question in idea["quiz"])


def test_balanced_allocation_has_exact_requested_amounts() -> None:
    """A balanced six-thousand plan matches the seven example jar amounts."""
    plan = allocation_plan("6000", "balanced")
    amounts = {item["idea_id"]: item["monthly_amount"] for item in plan["items"]}
    assert amounts == {
        "index-sip": Decimal("1800.00"),
        "equity-funds": Decimal("750.00"),
        "elss": Decimal("450.00"),
        "ppf": Decimal("900.00"),
        "debt-fund": Decimal("900.00"),
        "gold": Decimal("600.00"),
        "fd-rd": Decimal("600.00"),
    }
    assert plan["total"] == Decimal("6000.00")
    assert plan["summary"] == "Your ₹6,000 each month, split into 7 jars."
    assert "direct-stocks" not in {item["idea_id"] for item in plan["items"]}


def test_aggressive_allocation_totals_match_sample_and_chosen_amount() -> None:  # Check the sample table totals.
    """Sum exact rows and keep the chosen monthly amount as the monthly total."""  # Explain the expected behavior.
    plan = allocation_plan("12000", "aggressive")  # Build the user's ₹12,000 sample plan.
    totals = plan["totals"]  # Read totals calculated by the backend.
    assert totals["monthly"] == sum(  # Confirm monthly total equals all monthly rows.
        (item["monthly_amount"] for item in plan["items"]), Decimal("0")  # Add each exact monthly row.
    )  # Finish checking the monthly rows.
    assert totals["monthly"] == Decimal("12000.00")  # Confirm the total matches the chosen amount.
    assert abs(totals["monthly"] - Decimal("12000.00")) <= Decimal("1")  # Allow the requested ₹1 tolerance.
    assert totals["five_year_middle"] == sum(  # Confirm the five-year total is a row sum.
        (item["growth"]["5"]["mid"] for item in plan["items"]), Decimal("0")  # Add every five-year row.
    )  # Finish checking the five-year rows.
    assert abs(totals["five_year_middle"] - Decimal("916838.11")) <= Decimal("1")  # Check the sample within ₹1.
    assert totals["ten_year_middle"] == sum(  # Confirm the ten-year total is a row sum.
        (item["growth"]["10"]["mid"] for item in plan["items"]), Decimal("0")  # Add every ten-year row.
    )  # Finish checking the ten-year rows.
    assert abs(totals["ten_year_middle"] - Decimal("2373797.54")) <= Decimal("1")  # Check the sample within ₹1.


@pytest.mark.parametrize("monthly_amount", ["500", "1234.56", "6000", "25000"])
@pytest.mark.parametrize("investor_type", ["conservative", "balanced", "aggressive"])
def test_allocation_total_is_exact_for_all_types(monthly_amount, investor_type) -> None:
    """Every supported plan adds up to the exact paise-rounded monthly amount."""
    plan = allocation_plan(monthly_amount, investor_type)
    assert plan["total"] == Decimal(monthly_amount).quantize(Decimal("0.01"))


def test_not_ready_user_has_locked_risky_ideas_and_no_plan_api_basis() -> None:
    """Very little emergency savings and costly debt lock riskier recommendations."""
    user = {
        "investor_type": "balanced",
        "goals": [],
        "monthly_amount": Decimal("1000"),
        "emergency_fund_months": Decimal("0.75"),
        "has_high_interest_debt": True,
        "ready": False,
    }
    ideas = ideas_for_user(user)
    assert len(ideas) >= 8
    risky_ideas = [idea for idea in ideas if idea["risk_level"] >= 3]
    assert risky_ideas
    assert all(idea["locked"] for idea in risky_ideas)
    assert all("Fix basics first" in idea["lock_reason"] for idea in risky_ideas)
    assert all(not idea["locked"] for idea in ideas if idea["risk_level"] < 3)


@pytest.mark.parametrize("idea_id", ["equity-funds", "direct-stocks"])
def test_short_goal_lowers_high_risk_match_score(idea_id) -> None:
    """A two-year goal lowers scores for ideas with risk level four and five."""
    ideas = load_investment_ideas()
    idea = next(item for item in ideas if item["id"] == idea_id)
    base = match_score(idea, {
        "investor_type": "aggressive",
        "goals": [],
        "monthly_amount": "5000",
        "ready": True,
    })
    short_goal = match_score(idea, {
        "investor_type": "aggressive",
        "goals": [{"years": 2}],
        "monthly_amount": "5000",
        "ready": True,
    })
    assert short_goal["match_score"] == base["match_score"] - 30


def test_expected_growth_example() -> None:
    """An 1800 monthly SIP at an assumed 12 percent matches the prompt estimate."""
    value = calculate_sip_future_value("1800", "12", "10")
    assert abs(value - Decimal("418210.34")) <= Decimal("1")
