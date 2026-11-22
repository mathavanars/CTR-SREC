"""Test one complete account and profile API journey."""

import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

TEST_DATABASE = Path(__file__).resolve().parent.parent.parent / "test_auth_profile.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
os.environ["JWT_SECRET"] = "test-secret-that-is-only-used-by-tests"

from fastapi.testclient import TestClient

from backend.app_config import APP_CREDIT
from backend.database import SessionLocal, engine
from backend.goal_logs import format_user_time
from backend.main import app, is_chat_allowed
from backend.models import InvestmentPlan, ProgressSnapshot, User

TEST_MARKET_SNAPSHOT = {
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
    "stale": True,
    "message": "Data may be outdated (last checked: 2026-01-01).",
}


@pytest.fixture(scope="module", autouse=True)
def reset_test_database():
    """Use one clean test database and close pooled connections before cleanup."""
    import backend.dashboard
    import backend.chat_tools
    import backend.main
    import backend.market_data
    import backend.plan_api
    import backend.report

    market_patch = pytest.MonkeyPatch()
    market_patch.setattr(
        backend.chat_tools,
        "get_market_snapshot",
        lambda refresh=False: TEST_MARKET_SNAPSHOT,
    )
    market_patch.setattr(backend.dashboard, "get_market_snapshot", lambda: TEST_MARKET_SNAPSHOT)
    market_patch.setattr(backend.plan_api, "get_market_snapshot", lambda: TEST_MARKET_SNAPSHOT)
    market_patch.setattr(backend.report, "get_market_snapshot", lambda: TEST_MARKET_SNAPSHOT)
    market_patch.setattr(
        backend.main,
        "ask_groq",
        lambda question, context: (
            "Mock coach answer.\n\nEducational guidance only, not licensed financial advice."
        ),
    )
    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)
    yield
    market_patch.undo()
    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)


def test_register_get_profile_put_profile_and_login() -> None:
    """Register, save a profile, read it and log in with the same account."""
    with TestClient(app) as client:
        register = client.post(
            "/auth/register",
            json={"email": "demo@example.com", "password": "strongpassword"},
        )
        assert register.status_code == 200
        token = register.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        market_snapshot = client.get("/market-snapshot", headers=headers)
        assert market_snapshot.status_code == 200
        assert market_snapshot.json()["metrics"]["repo_rate"]["source_url"]
        refreshed_market = client.post("/market-snapshot/refresh", headers=headers)
        assert refreshed_market.status_code == 200
        onboarding = client.get("/onboarding/status", headers=headers)
        assert onboarding.status_code == 200
        assert onboarding.json()["onboarding_step"] == 0
        assert onboarding.json()["next_page"] == "money-details"

        empty_profile = client.get("/profile", headers=headers)
        assert empty_profile.status_code == 200
        assert empty_profile.json()["income"] is None

        empty_health = client.get("/health-score", headers=headers)
        assert empty_health.status_code == 409
        assert empty_health.json()["detail"] == "onboarding_incomplete"
        empty_plan = client.post(
            "/allocation-plan",
            headers=headers,
            json={"monthly_amount": "500"},
        )
        assert empty_plan.status_code == 409
        empty_projector = client.get("/plan/projector", headers=headers)  # Check the projector before a plan is saved.
        assert empty_projector.status_code == 200  # Return a friendly empty response instead of an error.
        assert empty_projector.json()["exists"] is False  # Tell the page there are no chosen parts yet.
        assert empty_projector.json()["parts"] == []  # Never invent investment ideas for an empty plan.

        saved_profile = client.put(
            "/profile",
            headers=headers,
            json={
                "income": "30000",
                "expenses": "20000",
                "savings": "60000",
                "debts": [
                    {"name": "Loan", "amount": "200000", "interest_rate": "12", "emi": "5000"}
                ],
                "goals": [
                    {"name": "Home", "amount": "1000000", "years": 5}
                ],
            },
        )
        assert saved_profile.status_code == 200
        assert saved_profile.json()["income"] == "30000"
        assert saved_profile.json()["goals"][0]["name"] == "Home"
        assert client.get("/onboarding/status", headers=headers).json()["onboarding_step"] == 1
        assert client.get("/health-score", headers=headers).status_code == 409

        login = client.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "strongpassword"},
        )
        assert login.status_code == 200
        assert login.json()["access_token"]
        login_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get(
            "/onboarding/status",
            headers=login_headers,
        ).json()["next_page"] == "retake-quiz"

        quiz = client.post(
            "/risk-quiz",
            headers=headers,
            json={"answers": [3, 3, 3, 3, 3, 3, 3]},
        )
        assert quiz.status_code == 200
        assert quiz.json()["investor_type"] == "balanced"
        assert client.get("/onboarding/status", headers=headers).json()["next_page"] == "investment-choices"
        assert client.get("/health-score", headers=headers).status_code == 409
        quiz_login = client.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "strongpassword"},
        )
        assert client.get(
            "/onboarding/status",
            headers={"Authorization": f"Bearer {quiz_login.json()['access_token']}"},
        ).json()["next_page"] == "investment-choices"
        assert client.get("/readiness", headers=headers).status_code == 409
        assert client.get("/asset-mix", headers=headers).status_code == 409

        ideas = client.get("/investment-ideas", headers=headers)
        assert ideas.status_code == 200
        assert len(ideas.json()["ideas"]) == 10
        assert len(ideas.json()["top_picks"]) == 3

        idea_details = client.get("/investment-ideas/index-sip", headers=headers)
        assert idea_details.status_code == 200
        assert idea_details.json()["name"] == "Index fund SIP"

        coach_ideas = client.post(
            "/chat",
            headers=headers,
            json={"question": "Where should I invest?"},
        )
        assert coach_ideas.status_code == 200
        assert coach_ideas.json()["answer"].startswith("Mock coach answer.")

        coach_plan = client.post(
            "/chat",
            headers=headers,
            json={"question": "Show my money plan", "monthly_amount": "6000"},
        )
        assert coach_plan.status_code == 200
        assert coach_plan.json()["answer"].startswith("Mock coach answer.")

        stock_question = client.post(
            "/chat",
            headers=headers,
            json={"question": "Which specific stock should I buy?"},
        )
        assert stock_question.json()["answer"].startswith("Mock coach answer.")

        suggestion = client.get(
            "/plan/suggestion?monthly_amount=6000",
            headers=headers,
        )
        assert suggestion.status_code == 200
        assert len(suggestion.json()["parts"]) == 5
        assert not any(part["idea_id"] == "elss" for part in suggestion.json()["parts"])
        assert suggestion.json()["scenario_totals"]["10"]["mid"]
        tax_suggestion = client.get(
            "/plan/suggestion?monthly_amount=6000&tax_saving_80c=true",
            headers=headers,
        )
        assert tax_suggestion.status_code == 200
        assert any(part["idea_id"] == "elss" for part in tax_suggestion.json()["parts"])
        small_suggestion = client.get(
            "/plan/suggestion?monthly_amount=1200",
            headers=headers,
        )
        assert small_suggestion.status_code == 200
        assert small_suggestion.json()["max_parts"] == 3
        assert len(small_suggestion.json()["parts"]) == 2
        parts = [
            {"idea_id": "index-sip", "share": "20"},
            {"idea_id": "ppf", "share": "20"},
            {"idea_id": "debt-fund", "share": "20"},
            {"idea_id": "gold", "share": "20"},
            {"idea_id": "fd-rd", "share": "20"},
        ]
        bad_shares = client.post(
            "/plan",
            headers=headers,
            json={
                "monthly_amount": "6000",
                "parts": [{"idea_id": "fd-rd", "share": "90"}],
            },
        )
        assert bad_shares.status_code == 400
        assert "exactly 100%" in bad_shares.json()["detail"]
        saved_plan = client.post(
            "/plan",
            headers=headers,
            json={
                "monthly_amount": "6000",
                "parts": parts,
                "tax_saving_80c": True,
            },
        )
        assert saved_plan.status_code == 200
        assert saved_plan.json()["tax_saving_80c"] is True
        why_parts = client.post(
            "/chat",
            headers=headers,
            json={"question": "Why only 5 parts?"},
        )
        assert why_parts.status_code == 200
        assert why_parts.json()["answer"].startswith("Mock coach answer.")
        assert client.get("/onboarding/status", headers=headers).json()["next_page"] == "plan-review"
        assert client.get("/health-score", headers=headers).status_code == 409
        review_login = client.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "strongpassword"},
        )
        assert client.get(
            "/onboarding/status",
            headers={"Authorization": f"Bearer {review_login.json()['access_token']}"},
        ).json()["next_page"] == "plan-review"

        analysis = client.post("/plan/analyze", headers=headers)
        assert analysis.status_code == 200
        assert analysis.json()["weighted_risk"] == "2.2"
        assert next(
            check for check in analysis.json()["checks"] if check["id"] == "risk-fit"
        )["status"] == "good"
        applied = client.post(
            "/plan/apply-fix",
            headers=headers,
            json={"fix_id": "affordability"},
        )
        assert applied.status_code == 200
        assert applied.json()["plan"]["monthly_amount"] == "5000.00"
        assert applied.json()["plan"]["is_stale"] is True
        analysis = client.post("/plan/analyze", headers=headers)
        assert analysis.status_code == 200
        comparison = client.get("/plan/compare", headers=headers)
        assert comparison.status_code == 200
        assert comparison.json()["your_analysis"]["score"]
        assert comparison.json()["your_analysis"]["weighted_risk"] == "2.2"
        assert isinstance(
            comparison.json()["suggested_analysis"]["growth"]["10"]["mid"], str
        )
        journey = client.get("/plan/journey", headers=headers)
        assert journey.status_code == 200
        assert len(journey.json()["tasks"]) == 5
        task = client.put(
            "/plan/tasks/task-index-sip",
            headers=headers,
            json={"completed": True},
        )
        assert task.status_code == 200
        assert task.json()["completed_tasks"] == 1
        confirmed = client.post(
            "/plan/confirm",
            headers=headers,
            json={"choice": "mine"},
        )
        assert confirmed.status_code == 200
        assert client.get("/onboarding/status", headers=headers).json()["next_page"] == "dashboard"
        finished_login = client.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "strongpassword"},
        )
        assert client.get(
            "/onboarding/status",
            headers={"Authorization": f"Bearer {finished_login.json()['access_token']}"},
        ).json()["next_page"] == "dashboard"
        three_part_plan = client.post("/plan", headers=headers, json={  # Save three choices for projector totals.
            "monthly_amount": "6000",
            "parts": [
                {"idea_id": "index-sip", "share": "20"},
                {"idea_id": "debt-fund", "share": "60"},
                {"idea_id": "ppf", "share": "20"},
            ],
        })
        assert three_part_plan.status_code == 200  # Confirm the three chosen parts were saved.
        projector = client.get("/plan/projector?years=10", headers=headers)  # Request only the saved plan's growth.
        assert projector.status_code == 200  # Confirm the plan projector endpoint works.
        projector_data = projector.json()  # Read the backend's exact table values.
        assert projector_data["parts_count"] == 3  # Return exactly one row for each chosen part.
        assert len(projector_data["parts"]) == 3  # Do not add any unchosen ideas.
        assert Decimal(projector_data["totals"]["monthly"]) == Decimal("6000.00")  # Match the user's saved monthly amount.
        assert Decimal(projector_data["totals"]["five_year_middle"]) == sum(  # Sum the three visible five-year rows.
            (Decimal(part["growth"]["5"]["mid"]) for part in projector_data["parts"]),
            Decimal("0"),
        )
        assert Decimal(projector_data["totals"]["ten_year_middle"]) == sum(  # Sum the three visible ten-year rows.
            (Decimal(part["growth"]["10"]["mid"]) for part in projector_data["parts"]),
            Decimal("0"),
        )
        with SessionLocal() as db:  # Add an old zero-share choice to check compatibility.
            saved_user = db.query(User).filter(User.email == "demo@example.com").one()  # Find only this test account.
            saved_row = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == saved_user.id).one()  # Find its saved plan.
            saved_row.parts = [*saved_row.parts, {"idea_id": "gold", "share": "0"}]  # Keep a zero-share row for the filter test.
            db.commit()  # Save the test-only legacy shape.
        zero_share_projector = client.get("/plan/projector?years=10", headers=headers)  # Read the plan with a zero-share part.
        assert zero_share_projector.status_code == 200  # Continue to show the other valid choices.
        assert len(zero_share_projector.json()["parts"]) == 3  # Keep the zero-share part out of the projector.
        assert all(part["idea_id"] != "gold" for part in zero_share_projector.json()["parts"])  # Never show an unchosen idea.
        assert client.get("/health-score", headers=headers).status_code == 200
        readiness = client.get("/readiness", headers=headers)
        assert readiness.status_code == 200
        assert readiness.json()["ready"] is True
        asset_mix = client.get("/asset-mix", headers=headers)
        assert asset_mix.status_code == 200
        assert asset_mix.json()["equity"] == 50
        assert asset_mix.json()["debt"] == 30
        assert asset_mix.json()["fd_cash"] == 10

        plan = client.post(
            "/allocation-plan",
            headers=headers,
            json={"monthly_amount": "6000"},
        )
        assert plan.status_code == 200
        assert plan.json()["ready"] is True
        assert plan.json()["total"] == "6000.00"
        assert plan.json()["totals"]["monthly"] == "6000.00"  # Match the user's chosen monthly amount.

        not_ready = client.put(
            "/profile",
            headers=headers,
            json={
                "income": "30000",
                "expenses": "20000",
                "savings": "15000",
                "debts": [
                    {"name": "Card", "amount": "50000", "interest_rate": "36", "emi": "3000"}
                ],
                "goals": [],
            },
        )
        assert not_ready.status_code == 200
        assert client.get("/plan", headers=headers).json()["is_stale"] is True
        blocked_plan = client.post(
            "/allocation-plan",
            headers=headers,
            json={"monthly_amount": "6000"},
        )
        assert blocked_plan.status_code == 200
        assert blocked_plan.json()["ready"] is False
        assert blocked_plan.json()["items"] == []

        logout = client.post("/auth/logout", headers=headers)
        assert logout.status_code == 200

        changed = client.post(
            "/auth/change-password",
            headers=headers,
            json={
                "old_password": "strongpassword",
                "new_password": "new-strong-password",
                "confirm_password": "new-strong-password",
            },
        )
        assert changed.status_code == 200
        assert client.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "new-strong-password"},
        ).status_code == 200

def test_unready_user_can_finish_with_basics_jars() -> None:
    """A user with little emergency money and costly debt can still finish setup safely."""
    with TestClient(app) as client:
        register = client.post(
            "/auth/register",
            json={"email": "basics@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
        client.put(
            "/profile",
            headers=headers,
            json={
                "income": "30000",
                "expenses": "20000",
                "savings": "15000",
                "debts": [
                    {"name": "Card", "amount": "50000", "interest_rate": "36", "emi": "3000"}
                ],
                "goals": [],
            },
        )
        client.post("/risk-quiz", headers=headers, json={"answers": [3] * 7})
        suggestion = client.get("/plan/suggestion?monthly_amount=6000", headers=headers)
        assert {part["idea_id"] for part in suggestion.json()["parts"]} == {
            "emergency-fund",
            "debt-payoff",
        }
        for locked_idea in ("index-sip", "elss", "direct-stocks"):
            locked = client.post(
                "/plan",
                headers=headers,
                json={
                    "monthly_amount": "6000",
                    "parts": [{"idea_id": locked_idea, "share": "100"}],
                },
            )
            assert locked.status_code == 400
            assert "locked" in locked.json()["detail"].lower()
        saved = client.post(
            "/plan",
            headers=headers,
            json={
                "monthly_amount": "6000",
                "parts": [
                    {"idea_id": "emergency-fund", "share": "50"},
                    {"idea_id": "debt-payoff", "share": "50"},
                ],
            },
        )
        assert saved.status_code == 200
        client.post("/plan/analyze", headers=headers)
        confirmed = client.post(
            "/plan/confirm",
            headers=headers,
            json={"choice": "mine"},
        )
        assert confirmed.status_code == 200
        assert client.get("/onboarding/status", headers=headers).json()["complete"] is True
        assert client.get("/health-score", headers=headers).status_code == 200


def test_chat_rate_limit_is_bounded() -> None:
    """The coach accepts twenty questions per minute and then asks the user to wait."""
    user_id = 987654
    assert all(is_chat_allowed(user_id) for _ in range(20))
    assert is_chat_allowed(user_id) is False


def test_goals_and_debts_patch_only_their_section_and_refresh_calculations() -> None:  # Cover section-only profile updates.
    """Keep other profile fields safe and refresh all affected summaries."""  # Describe the required partial update behavior.
    with TestClient(app) as client:  # Use an isolated client for this full account journey.
        register = client.post("/auth/register", json={"email": "sections@example.com", "password": "strongpassword"})  # Create a new test account.
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}  # Sign in to the test account.
        original_profile = client.put("/profile", headers=headers, json={  # Save the profile facts that must be preserved.
            "income": "30000",  # Give calculations a monthly income.
            "expenses": "10000",  # Give calculations monthly expenses.
            "savings": "60000",  # Provide a six-month emergency fund.
            "debts": [{"name": "Card", "amount": "50000", "interest_rate": "36", "emi": "3000"}],  # Add one high-interest debt.
            "goals": [{"name": "Home", "amount": "1000000", "years": 5}],  # Add one starting goal.
        })  # Finish creating the baseline profile.
        assert original_profile.status_code == 200  # Confirm the baseline profile saved.
        client.post("/risk-quiz", headers=headers, json={"answers": [3] * 7})  # Finish the risk quiz without changing the profile sections.
        saved = client.post("/plan", headers=headers, json={"monthly_amount": "5000", "parts": [{"idea_id": "fd-rd", "share": "100"}]})  # Save a plan for goal chance calculations.
        assert saved.status_code == 200  # Confirm the plan is ready for review.
        confirmed = client.post("/plan/confirm", headers=headers, json={"choice": "mine"})  # Complete setup with the saved plan.
        before_chance = confirmed.json()["analysis"]["goal"]["chance_percent"]  # Remember the original goal chance.
        before_step = client.get("/onboarding/status", headers=headers).json()["onboarding_step"]  # Remember the setup step.
        changed_goal = client.patch("/profile/goals", headers=headers, json={"goals": [{"name": "Home", "amount": "2000000", "years": 3}]})  # Change only the goal target.
        assert changed_goal.status_code == 200  # Confirm the goal edit succeeded.
        changed_profile = changed_goal.json()["profile"]  # Read the profile returned by the partial update.
        assert changed_profile["income"] == "30000"  # Keep income unchanged.
        assert changed_profile["expenses"] == "10000"  # Keep expenses unchanged.
        assert changed_profile["savings"] == "60000"  # Keep savings unchanged.
        assert changed_profile["debts"][0]["name"] == "Card"  # Keep debts unchanged.
        assert changed_profile["goals"][0]["amount"] == "2000000"  # Save the new goal amount.
        assert changed_goal.json()["plan_analysis"]["goal"]["amount"] == "2000000"  # Recalculate using the new goal amount.
        assert changed_goal.json()["plan_analysis"]["goal"]["years"] == 3  # Recalculate using the new goal years.
        assert changed_goal.json()["plan_analysis"]["goal"]["chance_percent"] != before_chance  # Recalculate the goal chance.
        assert changed_goal.json()["message"] == "Saved. Your numbers are updated."  # Return the requested save message.
        assert changed_goal.json()["plan_notice"] == "Your goals/debts changed. Re-check your plan."  # Return the plan reminder.
        assert client.get("/onboarding/status", headers=headers).json()["onboarding_step"] == before_step  # Keep onboarding progress unchanged.
        changed_debt = client.patch("/profile/debts", headers=headers, json={"debts": [{"name": "Loan", "amount": "40000", "interest_rate": "12", "emi": "2000"}]})  # Change only the debt section.
        assert changed_debt.status_code == 200  # Confirm the debt edit succeeded.
        debt_profile = changed_debt.json()["profile"]  # Read the updated debt profile.
        assert debt_profile["income"] == "30000"  # Keep income unchanged.
        assert debt_profile["expenses"] == "10000"  # Keep expenses unchanged.
        assert debt_profile["savings"] == "60000"  # Keep savings unchanged.
        assert debt_profile["goals"][0]["amount"] == "2000000"  # Keep the new goal unchanged.
        assert client.get("/onboarding/status", headers=headers).json()["onboarding_step"] == before_step  # Keep setup progress unchanged after debt edits.
        removed_debt = client.patch("/profile/debts", headers=headers, json={"debts": []})  # Remove the only debt.
        assert removed_debt.status_code == 200  # Confirm the debt removal succeeded.
        assert removed_debt.json()["profile"]["debts"] == []  # Confirm no debt remains.
        assert removed_debt.json()["health_score"]["debt_to_income_ratio"] == "0.00"  # Recalculate the debt ratio as zero.
        assert removed_debt.json()["readiness"]["has_high_interest_debt"] is False  # Recalculate readiness without the debt.
        assert removed_debt.json()["readiness"]["ready"] is True  # Confirm the remaining basics are ready.
        assert removed_debt.json()["money_left_monthly"] == "20000.00"  # Recalculate monthly money left.
        assert removed_debt.json()["plan_analysis"]["goal"]["amount"] == "2000000"  # Keep the updated goal in plan analysis.
        invalid_years = client.patch("/profile/goals", headers=headers, json={"goals": [{"name": "Trip", "amount": "1000", "years": 0}]})  # Try an unsupported goal timeline.
        assert invalid_years.status_code == 422  # Reject zero years.
        assert "Years to reach a goal must be from 1 to 50." in str(invalid_years.json()["detail"])  # Show a friendly timeline error.
        empty_name = client.patch("/profile/goals", headers=headers, json={"goals": [{"name": "  ", "amount": "1000", "years": 1}]})  # Try an empty goal name.
        assert empty_name.status_code == 422  # Reject an empty name.
        assert "Goal name cannot be empty." in str(empty_name.json()["detail"])  # Show a friendly name error.
        empty_debt_name = client.patch("/profile/debts", headers=headers, json={"debts": [{"name": "  ", "amount": "1000", "interest_rate": "10", "emi": "100"}]})  # Try an empty debt name.
        assert empty_debt_name.status_code == 422  # Reject an empty debt name.
        assert "Debt name cannot be empty." in str(empty_debt_name.json()["detail"])  # Show a friendly debt-name error.
        zero_amount = client.patch("/profile/goals", headers=headers, json={"goals": [{"name": "Trip", "amount": "0", "years": 1}]})  # Try a zero goal amount.
        assert zero_amount.status_code == 422  # Reject a non-positive goal amount.
        assert "Goal amount must be greater than zero." in str(zero_amount.json()["detail"])  # Show a friendly amount error.
        negative_emi = client.patch("/profile/debts", headers=headers, json={"debts": [{"name": "Loan", "amount": "1000", "interest_rate": "10", "emi": "-1"}]})  # Try a negative monthly payment.
        assert negative_emi.status_code == 422  # Reject a negative EMI.
        assert "Monthly EMI cannot be negative." in str(negative_emi.json()["detail"])  # Show a friendly EMI error.
        high_interest = client.patch("/profile/debts", headers=headers, json={"debts": [{"name": "Loan", "amount": "1000", "interest_rate": "61", "emi": "100"}]})  # Try a rate above the supported range.
        assert high_interest.status_code == 422  # Reject an interest rate above sixty percent.
        assert "Interest rate must be between 0 and 60%." in str(high_interest.json()["detail"])  # Show a friendly rate error.


def test_goal_investment_logs_audit_undo_snapshots_and_owner_checks() -> None:  # Cover secure monthly goal logs.
    """Keep actual log changes, values and history private to the signed-in user."""  # Describe the account safety rule.
    with TestClient(app) as client:  # Use a real local API client for both test accounts.
        alice_register = client.post("/auth/register", json={"email": "logs-a@example.com", "password": "strongpassword"})  # Create the first account.
        alice_headers = {"Authorization": f"Bearer {alice_register.json()['access_token']}"}  # Sign in as the first user.
        alice_profile = client.put("/profile", headers=alice_headers, json={  # Give the first user one dated goal.
            "income": "50000",  # Save monthly income for warning calculations.
            "expenses": "10000",  # Save monthly expenses.
            "savings": "20000",  # Save emergency savings.
            "debts": [],  # Keep the test account free of debt.
            "goals": [{"name": "Home", "amount": "1000000", "years": 5, "start_date": "2025-01-01"}],  # Allow backdated entries.
        })  # Finish creating the first profile.
        alice_goal_id = alice_profile.json()["goals"][0]["id"]  # Keep the stable goal ID for its private routes.
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()  # Use the same calendar timezone as the app.
        current_month = today.strftime("%Y-%m-01")  # Choose the current month for the first entry.
        first_log = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={  # Record the first monthly investment.
            "month": current_month,  # Save the selected calendar month.
            "amount": "6000",  # Save the exact monthly amount.
            "part_id": None,  # Leave the optional plan part blank.
            "note": "First entry",  # Keep one short note with the record.
        })  # Finish the first log request.
        assert first_log.status_code == 200  # Confirm the first log was saved.
        alice_log_id = first_log.json()["log"]["id"]  # Keep the new row ID for edit and delete checks.
        assert first_log.json()["log"]["status"] == "Added"  # Show the initial log status.
        assert first_log.json()["log"]["created_at"].endswith("Z")  # Return stored timestamps as UTC.
        duplicate = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={  # Try a second row for the same month.
            "month": current_month,  # Keep the duplicate month the same.
            "amount": "0",  # Use zero to represent a skipped contribution.
        })  # Finish the duplicate check.
        assert duplicate.json()["needs_choice"] is True  # Ask whether the user wants to add or edit.
        added_skip = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={  # Confirm a second row for the month.
            "month": current_month,  # Keep the same month.
            "amount": "0",  # Save the skipped month honestly as zero.
            "add_to_month": True,  # Confirm the add-to-month choice.
        })  # Finish saving the skipped update.
        assert added_skip.status_code == 200  # Confirm the skipped entry is saved.
        edited = client.put(f"/logs/{alice_log_id}", headers=alice_headers, json={  # Edit the original entry.
            "month": current_month,  # Keep its month unchanged.
            "amount": "7000",  # Change the saved amount.
            "note": "Updated entry",  # Change the note too.
            "add_to_month": True,  # Keep the existing skip row in the same month.
        })  # Finish the edit request.
        assert edited.status_code == 200  # Confirm the edit succeeded.
        assert edited.json()["log"]["status"] == "Edited"  # Mark the visible row as edited.
        assert edited.json()["log"]["history"][0]["old_amount"] == "6000.00"  # Keep the prior amount in audit history.
        assert edited.json()["log"]["history"][0]["new_amount"] == "7000.00"  # Keep the new amount in audit history.
        assert edited.json()["log"]["history"][0]["changed_by"] is not None  # Record who changed the amount.
        assert edited.json()["log"]["history"][0]["changed_at"].endswith("Z")  # Store the audit time in UTC.
        assert edited.json()["progress"]["total_invested"] == "7000.00"  # Recalculate active money from saved logs.
        deleted = client.delete(f"/logs/{alice_log_id}", headers=alice_headers)  # Soft-delete the edited amount.
        assert deleted.status_code == 200  # Confirm the delete request succeeded.
        assert deleted.json()["log"]["status"] == "Deleted"  # Keep deleted history visible.
        assert deleted.json()["undo_until"]  # Return a ten-second undo deadline.
        assert deleted.json()["log"]["history"][0]["action"] == "Deleted"  # Audit the delete action.
        after_delete = client.get(f"/goals/{alice_goal_id}/progress", headers=alice_headers)  # Recalculate after the soft delete.
        assert after_delete.json()["total_invested"] == "0.00"  # Exclude the deleted amount from totals.
        export = client.get(f"/goals/{alice_goal_id}/logs/export", headers=alice_headers)  # Download the entire history.
        assert export.status_code == 200  # Confirm the CSV route is available.
        assert "Deleted" in export.text  # Keep deleted rows in the exported history.
        undone = client.post(f"/logs/{alice_log_id}/undo", headers=alice_headers)  # Restore the soft-deleted entry.
        assert undone.status_code == 200  # Confirm the undo is inside the allowed window.
        assert undone.json()["progress"]["total_invested"] == "7000.00"  # Include the restored amount again.
        assert undone.json()["log"]["history"][0]["action"] == "Restored"  # Keep undo in the audit history.
        snapshot = client.post(f"/goals/{alice_goal_id}/value", headers=alice_headers, json={"value": "25000"})  # Save a real account value.
        assert snapshot.status_code == 200  # Confirm the dated snapshot was saved.
        assert snapshot.json()["progress"]["value_label"] == "Actual (you entered)"  # Use the actual-value label.
        assert snapshot.json()["progress"]["latest_value_snapshot"]["value"] == "25000.00"  # Return the latest saved value.
        assert snapshot.json()["progress"]["value_today"] == "25000.00"  # Use the entered snapshot as today's value.
        goal_coach = client.post("/chat", headers=alice_headers, json={"question": "Am I on track?"})  # Ask the coach to read the saved goal progress.
        assert goal_coach.status_code == 200  # Keep the goal-progress coach available.
        assert goal_coach.json()["answer"].startswith("Mock coach answer.")  # Route goal questions through the LLM.
        month_number = int(current_month[5:7])  # Choose the selected month for history filtering.
        year_number = int(current_month[:4])  # Choose the selected year for history filtering.
        for amount in range(10):  # Add enough rows to test the ten-row history pages.
            page_log = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={  # Save another row in the selected month.
                "month": current_month,  # Keep the filter month consistent.
                "amount": str(amount),  # Use a valid zero-or-positive amount.
                "add_to_month": True,  # Confirm multiple rows in a month.
            })  # Finish saving one history row.
            assert page_log.status_code == 200  # Confirm every history row was saved.
        page_one = client.get(  # Request the first filtered history page.
            f"/goals/{alice_goal_id}/logs?month={month_number}&year={year_number}&page=1",  # Apply both filters.
            headers=alice_headers,  # Read history as its owner.
        )  # Finish the first page request.
        page_two = client.get(  # Request the next filtered history page.
            f"/goals/{alice_goal_id}/logs?month={month_number}&year={year_number}&page=2",  # Keep the same filters.
            headers=alice_headers,  # Read history as its owner.
        )  # Finish the second page request.
        assert page_one.json()["total"] == 12  # Include both original entries and ten new rows.
        assert len(page_one.json()["logs"]) == 10  # Return at most ten entries per page.
        assert len(page_two.json()["logs"]) == 2  # Return the remaining rows on the next page.
        assert page_one.json()["logs"][0]["id"] > page_one.json()["logs"][1]["id"]  # Show newest-created rows first.
        future_month = "2026-12-01" if today.year == 2026 and today.month == 11 else f"{today.year + (today.month == 12):04d}-{today.month % 12 + 1:02d}-01"  # Make one future month for validation.
        future = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={"month": future_month, "amount": "1"})  # Try to log a future month.
        assert future.status_code == 422  # Reject a future month.
        assert "Choose this month or an earlier month." in str(future.json()["detail"])  # Show a friendly month error.
        negative = client.post(f"/goals/{alice_goal_id}/logs", headers=alice_headers, json={"month": current_month, "amount": "-1"})  # Try to save a negative amount.
        assert negative.status_code == 422  # Reject negative money.
        assert "Amount invested cannot be negative." in str(negative.json()["detail"])  # Show a friendly amount error.
        bob_register = client.post("/auth/register", json={"email": "logs-b@example.com", "password": "strongpassword"})  # Create a second, unrelated account.
        bob_headers = {"Authorization": f"Bearer {bob_register.json()['access_token']}"}  # Sign in as the second user.
        bob_profile = client.put("/profile", headers=bob_headers, json={  # Give the second account a different goal.
            "income": "40000",  # Save separate income.
            "expenses": "10000",  # Save separate expenses.
            "savings": "10000",  # Save separate savings.
            "debts": [],  # Keep the second account free of debt.
            "goals": [{"name": "Study", "amount": "100000", "years": 2}],  # Create a private second goal.
        })  # Finish creating the second profile.
        bob_goal_id = bob_profile.json()["goals"][0]["id"]  # Keep the second user's goal ID.
        assert client.get(f"/goals/{alice_goal_id}/progress", headers=bob_headers).status_code == 404  # Hide the first user's progress.
        assert client.get(f"/goals/{alice_goal_id}/logs", headers=bob_headers).status_code == 404  # Hide the first user's history.
        assert client.get(f"/goals/{alice_goal_id}/logs/export", headers=bob_headers).status_code == 404  # Hide the first user's CSV.
        assert client.post(f"/goals/{alice_goal_id}/logs", headers=bob_headers, json={"month": current_month, "amount": "1"}).status_code == 404  # Hide the first user's goal on create.
        assert client.put(f"/logs/{alice_log_id}", headers=bob_headers, json={"month": current_month, "amount": "1"}).status_code == 404  # Hide the first user's log on edit.
        assert client.delete(f"/logs/{alice_log_id}", headers=bob_headers).status_code == 404  # Hide the first user's log on delete.
        assert client.post(f"/logs/{alice_log_id}/undo", headers=bob_headers).status_code == 404  # Hide the first user's log on undo.
        assert client.get(f"/goals/{bob_goal_id}/progress", headers=bob_headers).status_code == 200  # Keep the second user's own goal accessible.
        utc_time = datetime(2026, 11, 21, 20, 35, tzinfo=ZoneInfo("UTC"))  # Use a fixed UTC time for timezone formatting.
        assert format_user_time(utc_time) == "22 Nov 2026, 2:05 AM"  # Show UTC storage in the default India timezone.


def test_report_handles_a_new_user_and_returns_real_pdf_and_csv() -> None:
    """Make complete reports for a new account without a plan, goals, logs or debts."""
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "newreport@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        report_response = client.get("/report/data?period=since_started", headers=headers)
        assert report_response.status_code == 200
        assert report_response.headers["Cache-Control"] == "no-store"
        report = report_response.json()
        assert report["app_credit"] == APP_CREDIT
        assert report["report_ready"] == {
            "has_profile": False,
            "has_plan": False,
            "has_goals": False,
            "has_logs": False,
            "has_debts": False,
        }
        assert "email" not in report
        assert "newreport@example.com" not in report_response.text
        assert len(report["summary"]) == 4
        assert report["past_present"]["empty"] is True
        assert len(report["past_present"]["history"]) == 1
        csv_response = client.get("/report/csv?period=since_started", headers=headers)
        assert csv_response.status_code == 200
        assert csv_response.headers["Cache-Control"] == "no-store"
        assert csv_response.text.startswith("Section,Item,Value")
        pdf_response = client.get("/report/pdf?period=since_started", headers=headers)
        assert pdf_response.status_code == 200
        assert pdf_response.headers["Cache-Control"] == "no-store"
        assert pdf_response.content.startswith(b"%PDF")
        assert len(pdf_response.content) > 1000
        assert "ArthMitra_Report_Newreport_" in pdf_response.headers["Content-Disposition"]
        if shutil.which("pdftotext"):
            pdf_text = subprocess.run(
                ["pdftotext", "-", "-"],
                input=pdf_response.content,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.decode("utf-8")
            for heading in (
                "1. COVER AND SUMMARY",
                "2. YOUR PROFILE TODAY",
                "3. YOUR JOURNEY SO FAR",
                "4. PAST VS PRESENT",
                "5. YOUR INVESTMENT PLAN",
                "6. GOALS",
                "7. DEBTS",
                "8. INVESTMENT LOG",
                "9. FUTURE OUTLOOK",
                "10. WARNINGS AND ALERTS",
                "11. ACTION PLAN",
                "12. MARKET SNAPSHOT",
                "13. HOW WE CALCULATED",
            ):
                assert heading in pdf_text
            assert pdf_text.count(
                "Educational guidance only. Not licensed financial advice."
            ) >= 1
            pages = [page for page in pdf_text.split("\f") if page.strip()]
            assert pages
            assert all(
                "Educational guidance only. Not licensed financial advice." in page
                for page in pages
            )
            assert all(APP_CREDIT in page for page in pages)


def test_report_snapshots_compare_values_and_keep_each_account_private() -> None:
    """Compare health snapshots and keep report values scoped to the signed-in user."""
    from backend.report import _change_row, check_wording_numbers

    row = _change_row("Health score", Decimal("60"), Decimal("75"))
    assert row["change"] == "15.00"
    assert row["change_percent"] == "25.00"
    assert row["arrow"] == "better"
    assert _change_row("Health score", Decimal("0"), Decimal("75"))["change_percent"] == "New"
    assert check_wording_numbers("Health score is 75.", {"health_score": "75.00"})
    assert not check_wording_numbers("Health score is 99.", {"health_score": "75.00"})
    with TestClient(app) as client:
        alice = client.post(
            "/auth/register",
            json={"email": "report-a@example.com", "password": "strongpassword"},
        )
        bob = client.post(
            "/auth/register",
            json={"email": "report-b@example.com", "password": "strongpassword"},
        )
        alice_headers = {"Authorization": f"Bearer {alice.json()['access_token']}"}
        bob_headers = {"Authorization": f"Bearer {bob.json()['access_token']}"}
        alice_profile = client.put(
            "/profile",
            headers=alice_headers,
            json={
                "income": "30000",
                "expenses": "12000",
                "savings": "60000",
                "debts": [],
                "goals": [],
            },
        )
        bob_profile = client.put(
            "/profile",
            headers=bob_headers,
            json={
                "income": "5000",
                "expenses": "1000",
                "savings": "2000",
                "debts": [],
                "goals": [],
            },
        )
        assert alice_profile.status_code == 200
        assert bob_profile.status_code == 200
        with SessionLocal() as db:
            alice_user = db.query(User).filter(User.email == "report-a@example.com").one()
            db.query(ProgressSnapshot).filter(
                ProgressSnapshot.user_id == alice_user.id,
            ).delete()
            now = datetime.now(timezone.utc)
            db.add_all([
                ProgressSnapshot(
                    user_id=alice_user.id,
                    health_score=Decimal("60"),
                    plan_score=None,
                    monthly_income=Decimal("30000"),
                    monthly_expenses=Decimal("12000"),
                    savings=Decimal("60000"),
                    money_left_monthly=Decimal("18000"),
                    savings_rate=Decimal("60"),
                    debt_to_income=Decimal("0"),
                    emergency_fund_months=Decimal("5"),
                    total_debt=Decimal("0"),
                    total_invested=Decimal("0"),
                    value_today=Decimal("0"),
                    goal_chances={},
                    created_at=now - timedelta(days=20),
                ),
                ProgressSnapshot(
                    user_id=alice_user.id,
                    health_score=Decimal("75"),
                    plan_score=None,
                    monthly_income=Decimal("30000"),
                    monthly_expenses=Decimal("12000"),
                    savings=Decimal("60000"),
                    money_left_monthly=Decimal("18000"),
                    savings_rate=Decimal("60"),
                    debt_to_income=Decimal("0"),
                    emergency_fund_months=Decimal("5"),
                    total_debt=Decimal("0"),
                    total_invested=Decimal("0"),
                    value_today=Decimal("0"),
                    goal_chances={},
                    created_at=now - timedelta(minutes=1),
                ),
            ])
            db.commit()
        alice_report = client.get("/report/data?period=last_6_months", headers=alice_headers).json()
        health_change = next(
            item for item in alice_report["past_present"]["rows"]
            if item["item"] == "Health score"
        )
        assert health_change["past"] == "60.00"
        assert health_change["present"] == "75.00"
        assert health_change["change"] == "15.00"
        assert health_change["change_percent"] == "25.00"
        assert alice_report["profile"]["metrics"]["emergency_fund_months"] == "5.00"
        assert alice_report["profile"]["metrics"]["savings_rate"] == "60.00"
        bob_report = client.get("/report/data", headers=bob_headers).json()
        assert bob_report["profile"]["metrics"]["income"] == "5000.00"
        assert "30000.00" not in str(bob_report)


def test_report_uses_only_saved_plan_parts_and_backend_growth_totals() -> None:
    """Keep report plan rows, growth values and totals tied to saved Decimal choices."""
    from backend.report import check_wording_numbers

    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "report-plan@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        profile = client.put(
            "/profile",
            headers=headers,
            json={
                "income": "30000",
                "expenses": "12000",
                "savings": "60000",
                "debts": [],
                "goals": [{"name": "Car", "amount": "800000", "years": 3}],
            },
        )
        assert profile.status_code == 200
        assert client.post("/risk-quiz", headers=headers, json={"answers": [3] * 7}).status_code == 200
        saved = client.post(
            "/plan",
            headers=headers,
            json={
                "monthly_amount": "6000",
                "parts": [
                    {"idea_id": "fd-rd", "share": "60"},
                    {"idea_id": "gold", "share": "40"},
                ],
            },
        )
        assert saved.status_code == 200
        assert client.post("/plan/confirm", headers=headers, json={"choice": "mine"}).status_code == 200
        report_response = client.get("/report/data?period=since_started", headers=headers)
        assert report_response.status_code == 200
        report = report_response.json()
        assert [part["idea_id"] for part in report["plan"]["parts"]] == ["fd-rd", "gold"]
        assert report["plan"]["total_share"] == "100.00"
        assert report["plan"]["total_monthly"] == "6000.00"
        assert sum(
            Decimal(part["monthly_amount"]) for part in report["plan"]["parts"]
        ) == Decimal("6000.00")
        assert report["outlook"]["rows"][1]["mid"]["invested"] == "216000.00"
        assert report["goals"][0]["name"] == "Car"
        assert report["profile"]["metrics"]["emergency_fund_months"] == "5.00"
        assert check_wording_numbers(" ".join(report["summary"]), report)
        pdf_response = client.get("/report/pdf?period=since_started", headers=headers)
        assert pdf_response.status_code == 200
        if shutil.which("pdftotext"):
            pdf_text = subprocess.run(
                ["pdftotext", "-", "-"],
                input=pdf_response.content,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.decode("utf-8")
            assert "₹6,000.00" in pdf_text
            assert "₹8,00,000.00" in pdf_text


def test_report_warning_rules_fire_and_stay_quiet_for_healthy_values() -> None:
    """Exercise every shared warning threshold with a failing and healthy case."""
    from backend.report import WARNING_RULES, _warning_items

    for rule in WARNING_RULES:
        failing = {}
        operator = rule["operator"]
        threshold = rule["threshold"]
        if operator == "lt":
            failing[rule["metric"]] = threshold - Decimal("1")
        elif operator == "gt":
            failing[rule["metric"]] = threshold + Decimal("1")
        elif operator == "gte":
            failing[rule["metric"]] = threshold
        elif operator == "false":
            failing[rule["metric"]] = False
        else:
            failing[rule["metric"]] = True
        assert rule["id"] in {
            warning["id"] for warning in _warning_items(failing)
        }
    healthy = {
        "emergency_fund_months": Decimal("6"),
        "max_interest_rate": Decimal("0"),
        "debt_to_income": Decimal("10"),
        "savings_rate": Decimal("60"),
        "plan_risk_ok": True,
        "short_goal_equity": False,
        "locked_money": False,
        "behind_percent": Decimal("0"),
        "missed_recent_months": Decimal("0"),
        "lowest_goal_chance": Decimal("80"),
        "market_age_days": Decimal("0"),
    }
    assert _warning_items(healthy) == []


def test_report_stress_test_adds_part_losses_before_showing_the_total() -> None:
    """Add the one-year shock for every selected part before showing a plan loss."""
    from backend.report import _future_outlook

    parts = [
        {"idea_id": "index-sip", "share": "30", "asset_class": "Equity", "monthly_amount": "1800", "expected_return_low": "5", "expected_return_mid": "11", "expected_return_high": "16"},
        {"idea_id": "equity-funds", "share": "12.5", "asset_class": "Equity", "monthly_amount": "750", "expected_return_low": "5", "expected_return_mid": "11", "expected_return_high": "16"},
        {"idea_id": "elss", "share": "7.5", "asset_class": "Equity", "monthly_amount": "450", "expected_return_low": "5", "expected_return_mid": "11", "expected_return_high": "16"},
        {"idea_id": "ppf", "share": "15", "asset_class": "Debt", "monthly_amount": "900", "expected_return_low": "4", "expected_return_mid": "7", "expected_return_high": "10"},
        {"idea_id": "debt-fund", "share": "15", "asset_class": "Debt", "monthly_amount": "900", "expected_return_low": "3", "expected_return_mid": "6", "expected_return_high": "9"},
        {"idea_id": "gold", "share": "10", "asset_class": "Gold", "monthly_amount": "600", "expected_return_low": "2", "expected_return_mid": "5", "expected_return_high": "8"},
        {"idea_id": "fd-rd", "share": "10", "asset_class": "Cash", "monthly_amount": "600", "expected_return_low": "4", "expected_return_mid": "7", "expected_return_high": "10"},
    ]
    report = _future_outlook(parts, Decimal("6000"), Decimal("100000"), Decimal("100000"), [])
    assert report["stress_test"]["fall_percent"] == "13.95"
    assert report["stress_test"]["loss"] == "13950.00"


def test_smart_monthly_amount_api_profile_and_coach_use_saved_values() -> None:
    """Keep the saved income pattern, preferred amount, report and coach in sync."""
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "smart-amount@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        saved = client.put("/profile", headers=headers, json={
            "income": "30000",
            "expenses": "18000",
            "savings": "60000",
            "debts": [{"name": "Loan", "amount": "1000", "interest_rate": "0", "emi": "6000"}],
            "goals": [{"name": "Car", "amount": "1000000", "years": 5}],
        })
        assert saved.status_code == 200
        onboarding_step = client.get("/onboarding/status", headers=headers).json()["onboarding_step"]
        initial = client.get("/smart-monthly-amount", headers=headers)
        assert initial.status_code == 200
        assert initial.json()["recommended"] == "4200"
        assert initial.json()["goal_need"] == "12123.22"
        changed = client.patch("/profile/investment-capacity", headers=headers, json={
            "income_stability": "sometimes_changes",
            "wanted_monthly_amount": "4000",
        })
        assert changed.status_code == 200
        assert changed.json()["suggestion"]["recommended"] == "3500"
        assert changed.json()["suggestion"]["verdict"] == "Tight"
        profile = client.get("/profile", headers=headers).json()
        assert profile["income_stability"] == "sometimes_changes"
        assert profile["wanted_monthly_amount"] == "4000"
        assert profile["income"] == "30000"
        assert profile["debts"][0]["emi"] == "6000"
        assert client.get("/onboarding/status", headers=headers).json()["onboarding_step"] == onboarding_step
        preview = client.post("/smart-monthly-amount/preview", headers=headers, json={
            "income_stability": "steady",
            "wanted_monthly_amount": "6000",
        })
        assert preview.status_code == 200
        assert preview.json()["verdict"] == "Too high, you may stop it later"
        good_preview = client.post("/smart-monthly-amount/preview", headers=headers, json={
            "income_stability": "steady",
            "wanted_monthly_amount": "4000",
        })
        assert good_preview.json()["verdict"] == "Good"
        coach = client.post("/chat", headers=headers, json={"question": "How much should I invest?"})
        assert coach.status_code == 200
        assert coach.json()["answer"].startswith("Mock coach answer.")
        report = client.get("/report/data", headers=headers)
        assert report.status_code == 200
        assert report.json()["monthly_amount_suggestion"]["recommended"] == "3500"


def test_smart_amount_growth_is_private_and_saving_keeps_plan_shares() -> None:
    """Keep amount previews owner-only and update only the saved plan's rupee total."""
    with TestClient(app) as client:
        alice = client.post("/auth/register", json={
            "email": "amount-growth-a@example.com",
            "password": "strongpassword",
        })
        alice_headers = {"Authorization": f"Bearer {alice.json()['access_token']}"}
        client.put("/profile", headers=alice_headers, json={
            "income": "30000",
            "expenses": "18000",
            "savings": "60000",
            "debts": [],
            "goals": [{"name": "Home", "amount": "1000000", "years": 10}],
        })
        quiz = client.post("/risk-quiz", headers=alice_headers, json={"answers": [3] * 7})
        assert quiz.status_code == 200
        saved = client.post("/plan", headers=alice_headers, json={
            "monthly_amount": "6000",
            "parts": [
                {"idea_id": "index-sip", "share": "30"},
                {"idea_id": "ppf", "share": "30"},
                {"idea_id": "fd-rd", "share": "40"},
            ],
        })
        assert saved.status_code == 200

        assert client.get("/smart-amount/growth?amount=3000&years=0", headers=alice_headers).status_code == 422
        assert client.put("/smart-amount", headers=alice_headers, json={
            "choice": "custom",
            "amount": "4201",
        }).status_code == 422
        old_projector = client.get("/plan/projector?years=10", headers=alice_headers).json()
        growth = client.get(
            "/smart-amount/growth?amount=6000&years=10",
            headers=alice_headers,
        )
        assert growth.status_code == 200
        assert growth.json()["series"][9]["high"] == old_projector["series"][9]["high"]
        assert growth.json()["totals"]["invested"] == "720000.00"

        changed = client.put("/smart-amount", headers=alice_headers, json={
            "choice": "recommended",
            "amount": "4200",
        })
        assert changed.status_code == 200
        assert changed.json()["message"] == "Saved. Re-check your plan."
        assert changed.json()["plan"]["monthly_amount"] == "4200.00"
        assert changed.json()["plan"]["parts"] == [
            {"idea_id": "index-sip", "share": "30"},
            {"idea_id": "ppf", "share": "30"},
            {"idea_id": "fd-rd", "share": "40"},
        ]
        assert changed.json()["plan"]["is_stale"] is True
        assert client.get("/profile", headers=alice_headers).json()["wanted_monthly_amount"] == "4200.00"
        refreshed_projector = client.get("/plan/projector", headers=alice_headers).json()
        assert refreshed_projector["totals"]["monthly"] == "4200.00"
        assert sum(
            (Decimal(part["monthly_amount"]) for part in refreshed_projector["parts"]),
            Decimal("0"),
        ) == Decimal("4200.00")

        expense_preview = client.get(
            "/smart-amount/growth?amount=0&years=10&expenses=16000",
            headers=alice_headers,
        )
        assert expense_preview.status_code == 200
        assert expense_preview.json()["amount"] == "14000.00"
        assert expense_preview.json()["expense_limit"]["current_expenses"] == "16000.00"
        assert client.get("/profile", headers=alice_headers).json()["expenses"] == "18000"

        coach = client.post("/chat", headers=alice_headers, json={
            "question": "What if I invest Rs 3,000?",
        })
        assert coach.status_code == 200
        assert coach.json()["answer"].startswith("Mock coach answer.")
        report = client.get("/report/data", headers=alice_headers).json()
        assert report["smart_amount_growth"]["amount"] == "4200.00"

        bob = client.post("/auth/register", json={
            "email": "amount-growth-b@example.com",
            "password": "strongpassword",
        })
        bob_headers = {"Authorization": f"Bearer {bob.json()['access_token']}"}
        client.put("/profile", headers=bob_headers, json={
            "income": "50000",
            "expenses": "10000",
            "savings": "50000",
            "debts": [],
            "goals": [],
        })
        bob_growth = client.get(
            "/smart-amount/growth?amount=6000&years=10",
            headers=bob_headers,
        )
        assert bob_growth.status_code == 200
        assert bob_growth.json()["parts"] != growth.json()["parts"]

        typed_want = client.put("/smart-amount", headers=alice_headers, json={
            "choice": "want",
            "amount": "4200.50",
        })
        assert typed_want.status_code == 200
        assert typed_want.json()["monthly_amount"] == "4200.50"


def test_new_user_dashboard_and_general_coach_question_use_empty_saved_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep new-account dashboard and general coach responses free of sample values."""
    import backend.main

    calls: list[tuple[str, dict[str, object]]] = []

    def fake_coach(question: str, context: dict[str, object]) -> str:
        calls.append((question, context))
        return "A SIP invests a set amount regularly.\n\nEducational guidance only, not licensed financial advice."

    monkeypatch.setattr(backend.main, "ask_groq", fake_coach)
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "coach-empty@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

        dashboard = client.get("/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["profile_complete"] is False
        assert dashboard.json()["investable_amount"] is None
        assert dashboard.json()["expense_limit"] is None
        assert dashboard.json()["growth"] is None
        assert dashboard.json()["scenarios"] == []

        answer = client.post(
            "/chat",
            headers=headers,
            json={"question": "What is a SIP?"},
        )
        assert answer.status_code == 200
        assert answer.json()["answer"].startswith("A SIP invests")
        assert calls[0][0] == "What is a SIP?"
        assert calls[0][1]["saved_profile"]["income"] is None
        assert calls[0][1]["saved_profile"]["goals"] == []
        assert calls[0][1]["investment_history"]["past_growth_available"] is False


def test_coach_receives_saved_profile_and_two_year_calculator_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass saved financial details and the persisted two-year estimate to the coach."""
    import backend.main

    calls: list[tuple[str, dict[str, object]]] = []

    def fake_coach(question: str, context: dict[str, object]) -> str:
        calls.append((question, context))
        return "Your saved details are available.\n\nEducational guidance only, not licensed financial advice."

    monkeypatch.setattr(backend.main, "ask_groq", fake_coach)
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "coach-saved@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        saved = client.put(
            "/profile",
            headers=headers,
            json={
                "income": "100000",
                "expenses": "20000",
                "savings": "100000",
                "debts": [{"name": "Education loan", "amount": "50000", "interest_rate": "10", "emi": "1000"}],
                "goals": [{"name": "Education", "amount": "500000", "years": 5}],
                "wanted_monthly_amount": "5000",
            },
        )
        assert saved.status_code == 200
        dashboard = client.get("/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["growth_two_years"]["years"] == 2

        answer = client.post(
            "/chat",
            headers=headers,
            json={"question": "How was the money growth in 2 years?"},
        )
        assert answer.status_code == 200
        assert answer.json()["answer"].startswith("Your saved details")
        question, context = calls[0]
        assert question == "How was the money growth in 2 years?"
        assert context["saved_profile"]["income"] == "100000"
        assert context["saved_profile"]["goals"][0]["name"] == "Education"
        assert context["saved_profile"]["debts"][0]["name"] == "Education loan"
        dashboard_result = context["latest_calculator_results"]["dashboard"]
        assert dashboard_result["growth_two_years"]["years"] == 2
        assert dashboard_result["growth_two_years"]["label"] == "Estimate"
        assert dashboard_result["growth_two_years"]["assumptions"]


def test_llm_failure_is_returned_as_clear_coach_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return a clear API error when the actual LLM service fails."""
    import backend.main
    from backend.llm import CoachServiceError

    def failed_coach(question: str, context: dict[str, object]) -> str:
        raise CoachServiceError("The AI coach could not get an answer from GroqCloud. Please try again.")

    monkeypatch.setattr(backend.main, "ask_groq", failed_coach)
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={"email": "coach-failure@example.com", "password": "strongpassword"},
        )
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        answer = client.post("/chat", headers=headers, json={"question": "Explain saving."})
        assert answer.status_code == 502
        assert "could not get an answer from GroqCloud" in answer.json()["detail"]
