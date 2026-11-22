"""Check plan scores, risk fit and separate-return growth calculations."""

from decimal import Decimal

from backend.analysis import analyze_plan
from backend.calculators import calculate_plan_growth


def _balanced_user() -> dict:
    """Make a ready balanced sample profile with a ten-year goal."""
    return {
        "income": "30000",
        "expenses": "20000",
        "savings": "60000",
        "debts": [],
        "goals": [{"name": "Home", "amount": "1000000", "years": 10}],
        "investor_type": "balanced",
    }


def _analysis(plan_parts: list[dict], amount: str = "6000", user: dict | None = None) -> dict:
    """Analyze the supplied parts using the same profile shape as the plan API."""
    return analyze_plan(
        user or _balanced_user(),
        {"monthly_amount": amount, "parts": plan_parts},
    )


def test_suggested_balanced_plan_has_weighted_risk_285() -> None:
    """The seven familiar jars fit the balanced 2.2-to-3.5 comfort range."""
    result = _analysis([
        {"idea_id": "index-sip", "share": "30"},
        {"idea_id": "equity-funds", "share": "12.5"},
        {"idea_id": "elss", "share": "7.5"},
        {"idea_id": "ppf", "share": "15"},
        {"idea_id": "debt-fund", "share": "15"},
        {"idea_id": "gold", "share": "10"},
        {"idea_id": "fd-rd", "share": "10"},
    ])
    checks = {check["id"]: check for check in result["checks"]}
    assert result["weighted_risk"] == Decimal("2.85")
    assert checks["risk-fit"]["status"] == "good"
    assert checks["risk-fit"]["score"] == 30


def test_one_equity_idea_is_a_diversification_problem_and_risk_warning() -> None:
    """One high-risk jar is not diverse and sits above balanced comfort."""
    result = _analysis([{"idea_id": "equity-funds", "share": "100"}])
    checks = {check["id"]: check for check in result["checks"]}
    assert result["weighted_risk"] == Decimal("4")
    assert checks["risk-fit"]["status"] == "warning"
    assert checks["diversification"]["status"] == "problem"


def test_zero_share_ideas_do_not_count_toward_diversification() -> None:
    """A selected but empty jar does not make a concentrated plan look diverse."""
    result = _analysis([
        {"idea_id": "index-sip", "share": "60"},
        {"idea_id": "fd-rd", "share": "40"},
        {"idea_id": "gold", "share": "0"},
    ])
    diversification = next(
        check for check in result["checks"] if check["id"] == "diversification"
    )
    assert diversification["status"] == "warning"
    assert "2 kinds of jars" in diversification["message"]


def test_diversification_fix_uses_an_existing_zero_share_jar() -> None:
    """A diversification fix can add share to an already selected empty jar."""
    result = _analysis([
        {"idea_id": "index-sip", "share": "70"},
        {"idea_id": "fd-rd", "share": "30"},
        {"idea_id": "gold", "share": "0"},
    ])
    fix = next(item for item in result["top_fixes"] if item["id"] == "diversification")
    shares = {part["idea_id"]: part["share"] for part in fix["parts"]}
    assert shares["gold"] == Decimal("20")
    assert sum(shares.values()) == Decimal("100")


def test_conservative_plan_above_risk_range_is_warned() -> None:
    """An index-heavy plan is above the conservative user's top risk level."""
    user = {**_balanced_user(), "investor_type": "conservative"}
    result = _analysis([
        {"idea_id": "index-sip", "share": "70"},
        {"idea_id": "fd-rd", "share": "30"},
    ], user=user)
    assert result["weighted_risk"] == Decimal("3.1")
    assert next(check for check in result["checks"] if check["id"] == "risk-fit")["status"] == "warning"


def test_near_goal_and_locked_money_warnings() -> None:
    """Short goals warn about equity and money locked for too long."""
    short_equity = _analysis(
        [{"idea_id": "index-sip", "share": "60"}, {"idea_id": "fd-rd", "share": "40"}],
        user={**_balanced_user(), "goals": [{"name": "Trip", "amount": "100000", "years": 2}]},
    )
    assert "Shares can fall" in next(
        check for check in short_equity["checks"] if check["id"] == "time-fit"
    )["message"]
    locked = _analysis(
        [
            {"idea_id": "ppf", "share": "20"},
            {"idea_id": "elss", "share": "20"},
            {"idea_id": "nps", "share": "20"},
            {"idea_id": "fd-rd", "share": "40"},
        ],
        user={**_balanced_user(), "goals": [{"name": "Study", "amount": "100000", "years": 4}]},
    )
    assert "Locked money cannot" in next(
        check for check in locked["checks"] if check["id"] == "time-fit"
    )["message"]


def test_over_budget_amount_is_allowed_but_warned() -> None:
    """An amount above the user's safe monthly amount is a warning, not a rejection."""
    user = {
        **_balanced_user(),
        "expenses": "24000",
        "savings": "72000",
    }
    result = _analysis(
        [{"idea_id": "fd-rd", "share": "100"}],
        amount="8000",
        user=user,
    )
    affordability = next(check for check in result["checks"] if check["id"] == "affordability")
    assert affordability["status"] == "warning"
    assert result["monthly_amount"] == Decimal("8000")


def test_growth_adds_each_part_at_its_own_return_rate() -> None:
    """Different return assumptions add to the required 10-year sum, not an average."""
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
    assert result["low"] == Decimal("1191113.46")
    assert result["mid"] == Decimal("1191113.46")
    assert result["high"] == Decimal("1191113.46")
    assert result["invested"] == Decimal("720000.00")


def test_not_ready_user_can_make_a_basics_first_plan() -> None:
    """Emergency savings and costly debt can be handled without a locked investment."""
    user = {
        **_balanced_user(),
        "savings": "15000",
        "debts": [
            {"name": "Card", "amount": "50000", "interest_rate": "36", "emi": "3000"}
        ],
    }
    result = _analysis([
        {"idea_id": "emergency-fund", "share": "50"},
        {"idea_id": "debt-payoff", "share": "50"},
    ], user=user)
    assert result["weighted_risk"] == Decimal("1")
    assert next(check for check in result["checks"] if check["id"] == "affordability")["status"] == "problem"
