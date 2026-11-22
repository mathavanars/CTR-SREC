"""Check private amount projections, separate return rates and expense limits."""

from decimal import Decimal

from backend.calculators import calculate_plan_growth
from backend.smart_amount import calculate_amount_growth


SNAPSHOT = {"metrics": {}}
SAVED_PARTS = [
    {"idea_id": "index-sip", "share": "24.1134", "expected_return_low": "5", "expected_return_mid": "11", "expected_return_high": "16"},
    {"idea_id": "fd-rd", "share": "75.8866", "expected_return_low": "4", "expected_return_mid": "7", "expected_return_high": "10"},
]
READY_PROFILE = {
    "income": "30000",
    "expenses": "18000",
    "savings": "60000",
    "debts": [{"name": "Loan", "amount": "200000", "interest_rate": "0", "emi": "6000"}],
    "goals": [{"name": "Home", "amount": "1000000", "years": 5}],
    "investor_type": "balanced",
}


def test_high_growth_scales_with_the_monthly_amount_and_keeps_each_part_rate() -> None:
    """Keep the saved-plan high case exact while changing only the monthly amount."""
    expected_high = {
        "3000": Decimal("684703.99"),
        "4200": Decimal("958585.58"),
        "5400": Decimal("1232467.17"),
        "6000": Decimal("1369407.97"),
    }
    for amount, expected in expected_high.items():
        result = calculate_amount_growth(
            amount,
            10,
            READY_PROFILE,
            SAVED_PARTS,
            SNAPSHOT,
        )
        assert result["mode"] == "growth"
        assert abs(Decimal(result["totals"]["high"]) - expected) <= Decimal("1")
        assert Decimal(result["totals"]["invested"]) == Decimal(amount) * 120

    six_thousand = calculate_amount_growth(
        "6000",
        10,
        READY_PROFILE,
        SAVED_PARTS,
        SNAPSHOT,
    )
    part_highs = [
        calculate_plan_growth([part], 10)["high"]
        for part in six_thousand["parts"]
    ]
    assert sum(part_highs, Decimal("0")) == Decimal(six_thousand["totals"]["high"])


def test_expense_limits_subtract_only_the_selected_amount_when_basics_are_ready() -> None:
    """Use income, EMI and the selected amount for the exact expense limit."""
    for amount, allowed, room in (
        ("3000", "21000.00", "3000.00"),
        ("4200", "19800.00", "1800.00"),
        ("5400", "18600.00", "600.00"),
        ("6000", "18000.00", "0.00"),
    ):
        result = calculate_amount_growth(
            amount,
            10,
            READY_PROFILE,
            SAVED_PARTS,
            SNAPSHOT,
        )
        assert result["expense_limit"]["highest_expenses_allowed"] == allowed
        assert result["expense_limit"]["room_left"] == room


def test_zero_surplus_has_tips_without_growth_and_basics_hide_investment_growth() -> None:
    """Show an actionable empty-budget state and basics timelines, never investment growth."""
    no_surplus = calculate_amount_growth(
        "3000",
        10,
        {
            **READY_PROFILE,
            "expenses": "24000",
        },
        SAVED_PARTS,
        SNAPSHOT,
    )
    assert no_surplus["mode"] == "no_surplus"
    assert no_surplus["series"] == []
    assert no_surplus["totals"] is None
    assert len(no_surplus["tips"]) == 3

    not_ready = calculate_amount_growth(
        "3000",
        10,
        {
            **READY_PROFILE,
            "savings": "0",
            "debts": [{"name": "Card", "amount": "10000", "interest_rate": "36", "emi": "1000"}],
        },
        SAVED_PARTS,
        SNAPSHOT,
    )
    assert not_ready["mode"] == "basics"
    assert not_ready["series"] == []
    assert not_ready["totals"] is None
    assert not_ready["basics"]["emergency_fund_months"] == 36
    assert not_ready["basics"]["debt"]["months_with_extra"] is not None
    assert Decimal(not_ready["basics"]["debt"]["interest_saved"]) > 0

