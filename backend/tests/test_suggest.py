"""Check smart suggestions, sourced scenarios and outage behavior."""

from decimal import Decimal

import pytest

from backend.calculators import calculate_smart_mix, calculate_stress_test, max_parts
from backend.suggest import build_smart_suggestion


MARKET = {
    "metrics": {
        "repo_rate": {"value": "6.50", "direction": "steady", "source_url": "https://rbi.org.in", "fetched_at": "2026-01-01"},
        "cpi_inflation": {"value": "5.22", "source_url": "https://mospi.gov.in", "fetched_at": "2026-01-01"},
        "sbi_1y_fd_rate": {"value": "6.80", "source_url": "https://sbi.co.in", "fetched_at": "2026-01-01"},
        "ppf_rate": {"value": "7.10", "source_url": "https://nsiindia.gov.in", "fetched_at": "2026-01-01"},
        "government_10y_yield": {"value": "6.80", "source_url": "https://rbi.org.in", "fetched_at": "2026-01-01"},
        "nifty_pe": {"value": "22.00", "source_url": "https://niftyindices.com", "fetched_at": "2026-01-01"},
        "nifty_pe_10y_average": {"value": "22.00", "source_url": "https://niftyindices.com/history", "fetched_at": "2026-01-01"},
        "gold_1y_change": {"value": "10.00", "source_url": "https://ibjarates.com", "fetched_at": "2026-01-01"},
    },
    "data_as_of": "2026-01-01",
    "stale": False,
    "message": "Data as of 2026-01-01.",
}
READY = {
    "ready": True,
    "emergency_fund_months": "3.00",
    "has_high_interest_debt": False,
}


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("800", 2), ("2000", 3), ("6000", 5), ("10000", 7)],
)
def test_part_cap_matches_monthly_amount_bands(amount, expected) -> None:
    """Every amount band returns the requested maximum part count."""
    assert max_parts(amount) == expected


@pytest.mark.parametrize(
    ("amount", "investor_type"),
    [("2000", "balanced"), ("6000", "conservative"), ("6000", "aggressive"), ("10000", "balanced")],
)
def test_parts_meet_minimums_and_add_up_exactly(amount, investor_type) -> None:
    """Every built plan stays within its cap and exact rupee and share totals."""
    plan = build_smart_suggestion(amount, investor_type, [], READY, MARKET)
    parts = plan["parts"]
    minimum = max(Decimal("500"), Decimal(amount) / Decimal("10"))
    assert len(parts) <= max_parts(amount)
    assert sum((part["share"] for part in parts), Decimal("0")) == Decimal("100.00")
    assert sum((part["monthly_amount"] for part in parts), Decimal("0")) == Decimal(amount).quantize(Decimal("0.01"))
    assert all(part["share"] >= Decimal("10") for part in parts)
    assert all(part["monthly_amount"] >= minimum for part in parts)
    if amount == "6000":
        assert len(parts) != 7


def test_conservative_and_aggressive_suggestions_are_different() -> None:
    """The same amount produces different class shares for different risk types."""
    conservative = build_smart_suggestion("6000", "conservative", [], READY, MARKET)
    aggressive = build_smart_suggestion("6000", "aggressive", [], READY, MARKET)
    assert conservative["mix"] != aggressive["mix"]
    assert conservative["parts"] != aggressive["parts"]


@pytest.mark.parametrize(
    ("years", "equity_cap"),
    [(2, Decimal("20")), (4, Decimal("50"))],
)
def test_near_goal_caps_equity_before_market_tilts(years, equity_cap) -> None:
    """A short goal keeps equity within its limit even for an aggressive investor."""
    result = calculate_smart_mix("aggressive", MARKET, years)
    assert result["mix"]["equity"] <= equity_cap


def test_goal_under_three_years_uses_one_safe_jar() -> None:
    """A two-year goal uses one FD/RD part instead of equity investments."""
    plan = build_smart_suggestion(
        "6000",
        "aggressive",
        [{"name": "Car", "amount": "100000", "years": 2}],
        READY,
        MARKET,
    )
    assert len(plan["parts"]) == 1
    assert plan["parts"][0]["idea_id"] == "fd-rd"
    assert plan["mix"]["equity"] <= Decimal("20")


def test_market_tilts_follow_rules_without_breaking_limits() -> None:
    """Hot inflation, valuation, RBI and gold inputs get checked tilt explanations."""
    hot_market = {
        **MARKET,
        "metrics": {
            **MARKET["metrics"],
            "cpi_inflation": {"value": "6.00"},
            "sbi_1y_fd_rate": {"value": "4.00"},
            "nifty_pe": {"value": "25.00"},
            "nifty_pe_10y_average": {"value": "20.00"},
            "repo_rate": {"value": "6.50", "direction": "falling"},
            "gold_1y_change": {"value": "30.00"},
        },
    }
    result = calculate_smart_mix("balanced", hot_market)
    assert sum(result["mix"].values(), Decimal("0")) == Decimal("100")
    assert Decimal("5") <= result["mix"]["gold"] <= Decimal("10")
    assert all(
        abs(result["mix"][asset] - result["base_mix"][asset]) <= Decimal("10")
        for asset in result["mix"]
    )
    assert result["risk_range"]["low"] <= result["weighted_risk"] <= result["risk_range"]["high"]
    assert any("Nifty valuation" in message for message in result["tilts"])


@pytest.mark.parametrize("investor_type", ["conservative", "balanced", "aggressive"])
def test_market_tilts_stay_bounded_and_risk_fits_when_goal_allows(investor_type) -> None:
    """Market tilts move each class by at most ten points and keep the risk band."""
    result = calculate_smart_mix(investor_type, MARKET)
    base = result["base_mix"]
    mix = result["mix"]
    assert sum(mix.values(), Decimal("0")) == Decimal("100")
    assert Decimal("5") <= mix["gold"] <= Decimal("10")
    assert all(abs(mix[name] - base[name]) <= Decimal("10") for name in base)
    assert result["risk_band_exception"] is False
    assert result["risk_range"]["low"] <= result["weighted_risk"] <= result["risk_range"]["high"]


def test_tax_saving_answer_is_required_before_elss_is_used() -> None:
    """ELSS appears only after the user opts in to the tax-saving question."""
    no_tax = build_smart_suggestion("10000", "balanced", [], READY, MARKET, False)
    yes_tax = build_smart_suggestion("10000", "balanced", [], READY, MARKET, True)
    assert "elss" not in {part["idea_id"] for part in no_tax["parts"]}
    assert "elss" in {part["idea_id"] for part in yes_tax["parts"]}


def test_unready_user_gets_basics_first_and_no_equity() -> None:
    """Costly debt and a small emergency fund pause equity investing."""
    not_ready = {
        "ready": False,
        "emergency_fund_months": "0.75",
        "has_high_interest_debt": True,
    }
    plan = build_smart_suggestion("6000", "balanced", [], not_ready, MARKET)
    assert [part["idea_id"] for part in plan["parts"]] == ["emergency-fund", "debt-payoff"]
    assert not any(part["asset_class"] == "equity" for part in plan["parts"])


def test_scenario_totals_sum_part_by_part_and_label_assumptions() -> None:
    """Five- and ten-year values are added from each part's own return case."""
    plan = build_smart_suggestion("6000", "balanced", [], READY, MARKET)
    for years in ("5", "10"):
        for level in ("low", "mid", "high"):
            total = sum(
                (part["growth"][years][level] for part in plan["parts"]),
                Decimal("0"),
            )
            assert plan["scenario_totals"][years][level] == total
    assert "Assumptions" in plan["label"]
    assert plan["why_this_plan"]["disclaimer"] == "This is not a prediction. It shows possible outcomes."


def test_balanced_stress_example_matches_the_requested_13_95_percent() -> None:
    """The requested sample plan loses 13.95% in the one-bad-year example."""
    parts = [
        {"idea_id": "index-sip", "asset_class": "equity", "share": "30"},
        {"idea_id": "equity-funds", "asset_class": "equity", "share": "12.5"},
        {"idea_id": "elss", "asset_class": "equity", "share": "7.5"},
        {"idea_id": "ppf", "asset_class": "debt", "share": "15"},
        {"idea_id": "debt-fund", "asset_class": "debt", "share": "15"},
        {"idea_id": "gold", "asset_class": "gold", "share": "10"},
        {"idea_id": "fd-rd", "asset_class": "cash", "share": "10"},
    ]
    result = calculate_stress_test("6000", parts)
    assert result["fall_percent"] == Decimal("13.95")
    assert result["loss_amount"] == Decimal("837.00")


def test_failed_market_fetch_uses_saved_snapshot_and_shows_old_date(monkeypatch) -> None:
    """A failed source stays safe, dated and visible in the outdated-data message."""
    from backend import market_data

    def fail_fetch(url):
        raise TimeoutError("public source timed out")

    monkeypatch.setattr(market_data, "_fetch_source", fail_fetch)
    snapshot = market_data.get_market_snapshot(refresh=True)
    assert snapshot["stale"] is True
    assert "Data may be outdated (last checked:" in snapshot["message"]
    assert snapshot["metrics"]["cpi_inflation"]["value"] == "5.22"
    assert snapshot["metrics"]["cpi_inflation"]["fetched_at"] == "2025-01-01"
    assert snapshot["metrics"]["cpi_inflation"]["source_url"].startswith("https://")


def test_sbi_parser_reads_revised_public_one_year_rate() -> None:
    """The SBI parser reads the revised public rate, not the senior-citizen rate."""
    from backend.market_data import _parse_source

    page = """
      <table><tr><th>Tenors</th><th>Existing Public</th><th>Revised Public</th>
      <th>Existing Senior</th><th>Revised Senior</th></tr>
      <tr><td>1 Year</td><td>6.00%</td><td>6.25%</td><td>6.50%</td><td>6.75%</td></tr></table>
    """
    assert _parse_source("sbi_deposits", page)["sbi_1y_fd_rate"] == 6.25


def test_implausible_market_value_is_rejected(monkeypatch) -> None:
    """A CPI value outside its believable range falls back to the saved figure."""
    from backend import market_data

    monkeypatch.setattr(market_data, "_fetch_source", lambda url: "not used")
    monkeypatch.setattr(
        market_data,
        "_parse_source",
        lambda group, page: {"cpi_inflation": 99} if group == "mospi_cpi" else {},
    )
    snapshot = market_data.get_market_snapshot(refresh=True)
    assert snapshot["metrics"]["cpi_inflation"]["value"] == "5.22"
    assert "cpi_inflation" in snapshot["stale_metrics"]
