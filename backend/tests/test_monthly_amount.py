"""Check the smart monthly amount suggestions and step-up examples."""

from decimal import Decimal

from backend.calculators import (
    calculate_sip_future_value_months,
    calculate_step_up_sip_future_value,
    suggest_monthly_amount,
)


def _sample_profile(wanted: str = "6000", stability: str = "steady") -> dict:
    """Make the requested monthly amount example easy to reuse in tests."""
    return {
        "income": "30000",
        "expenses": "18000",
        "savings": "60000",
        "debts": [{"name": "Loan", "amount": "1000", "interest_rate": "0", "emi": "6000"}],
        "goals": [{"name": "Car", "amount": "1000000", "years": 5}],
        "wanted_monthly_amount": wanted,
        "income_stability": stability,
    }


def test_steady_income_returns_requested_amounts_need_and_verdicts() -> None:
    """Use the three steady-income rules and the five-year goal example."""
    too_high = suggest_monthly_amount(_sample_profile())
    local_time = too_high["calculated_at_local"].split(", ")[1]
    assert local_time[0] != "0"
    assert too_high["surplus"] == Decimal("6000.00")
    assert too_high["comfortable"] == Decimal("3000")
    assert too_high["recommended"] == Decimal("4200")
    assert too_high["stretch"] == Decimal("5400")
    assert too_high["verdict"] == "Too high, you may stop it later"
    assert too_high["goal_need"] == Decimal("12123.22")
    assert too_high["goal_chance_at_recommended"] == Decimal("34.64")
    assert too_high["months_to_goal_at_recommended"] == 122
    assert all(
        amount % Decimal("100") == 0 and amount <= too_high["surplus"]
        for amount in (too_high["comfortable"], too_high["recommended"], too_high["stretch"])
    )
    good = suggest_monthly_amount(_sample_profile(wanted="4000"))
    assert good["verdict"] == "Good"


def test_changing_income_reduces_the_amounts() -> None:
    """Use the requested smaller amounts when income sometimes changes."""
    result = suggest_monthly_amount(_sample_profile(stability="sometimes_changes"))
    assert (result["comfortable"], result["recommended"], result["stretch"]) == (
        Decimal("2500"),
        Decimal("3500"),
        Decimal("4500"),
    )


def test_high_interest_debt_sends_recommended_amount_to_basics() -> None:
    """Pause investing and estimate emergency-fund time when basics are not ready."""
    result = suggest_monthly_amount({
        "income": "25000",
        "expenses": "20000",
        "savings": "15000",
        "debts": [{"name": "Card", "amount": "10000", "interest_rate": "36", "emi": "4000"}],
    })
    assert result["surplus"] == Decimal("1000.00")
    assert result["recommended"] == Decimal("700")
    assert result["ready_to_invest"] is False
    assert result["invest"] == Decimal("0")
    assert result["basics"] == Decimal("700")
    assert result["emergency_fund_gap"] == Decimal("45000.00")
    assert result["emergency_fund_months_at_basics"] == 65


def test_zero_or_negative_surplus_returns_tips_and_no_investment() -> None:
    """Show clear money-saving tips rather than raising on an empty budget."""
    for expenses in ("24000", "25000"):
        result = suggest_monthly_amount({
            "income": "25000",
            "expenses": expenses,
            "savings": "0",
            "debts": [{"emi": "1000", "interest_rate": "0"}],
        })
        assert result["surplus"] <= Decimal("0")
        assert result["invest"] == Decimal("0")
        assert result["recommended"] == Decimal("0")
        assert len(result["tips"]) == 3


def test_step_up_zero_matches_flat_sip_and_ten_percent_grows_more() -> None:
    """Keep the zero-step example identical to the existing annuity-due SIP."""
    flat = calculate_sip_future_value_months("4200", "12", 60)
    no_step = calculate_step_up_sip_future_value("4200", "12", 60, "0")
    step_up = calculate_step_up_sip_future_value("4200", "12", 60, "10")
    assert no_step == flat
    assert step_up > flat

