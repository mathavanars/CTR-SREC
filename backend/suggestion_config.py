"""Keep smart-plan assumptions together so they are easy to review."""

from decimal import Decimal

# These are the standard starting shares for each investor type.
BASE_MIXES = {
    "conservative": {"equity": 20, "debt": 40, "gold": 10, "cash": 30},
    "balanced": {"equity": 50, "debt": 30, "gold": 10, "cash": 10},
    "aggressive": {"equity": 70, "debt": 15, "gold": 10, "cash": 5},
}

# These ranges describe the plan risk score used by this learning tool.
RISK_RANGES = {
    "conservative": (1.0, 2.2),
    "balanced": (2.2, 3.5),
    "aggressive": (3.5, 5.0),
}

# These simple weights keep the plan risk check consistent across asset groups.
ASSET_RISK = {"equity": 5.0, "debt": 1.5, "gold": 2.0, "cash": 0.5}

# The equity risk premium is a teaching assumption added to the 10-year bond yield.
EQUITY_RISK_PREMIUM = 4.5

# These settings control the low and high examples for non-equity investments.
SCENARIO_OFFSETS = {"standard": 3.0, "equity_low": 6.0, "equity_high": 5.0}

# These shocks describe one bad year and do not predict a future loss.
STRESS_SHOCKS = {
    "equity": -25.0,
    "gold": -10.0,
    "debt-fund": -3.0,
    "no_drop": 0.0,
}

# These are simple monthly-budget rules of thumb, not promises of affordability.
MONTHLY_AMOUNT_SHARES = {
    "comfortable": Decimal("0.50"),
    "recommended": Decimal("0.70"),
    "stretch": Decimal("0.90"),
    "cushion": Decimal("0.10"),
}

# Changing income lowers the suggested amounts to leave more room for surprises.
INCOME_STABILITY_MULTIPLIERS = {
    "steady": Decimal("1.00"),
    "sometimes_changes": Decimal("0.85"),
    "irregular": Decimal("0.70"),
}

# Use a clear teaching rate only when the user has not saved an investment plan.
DEFAULT_GOAL_RETURN_RATE = Decimal("12.00")

# Step-up examples add ten percent to the monthly amount once each year.
DEFAULT_ANNUAL_STEP_UP_PERCENT = Decimal("10")
