"""Create the first running version of the ArthMitra API."""

import subprocess
import sys
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from backend.analysis import analyze_plan  # Recalculate a saved plan after profile edits.
from backend.auth import create_access_token, get_current_user, hash_password, verify_password
from backend.database import get_db, engine
from backend.models import (
    Base,
    DashboardResult,
    GoalValueSnapshot,
    InvestmentLog,
    InvestmentPlan,
    Profile,
    ProgressSnapshot,
    User,
)
from backend.dashboard import build_dashboard_result
from backend.report import record_progress_snapshot, router as report_router
from backend.plan_api import router as plan_router
from backend.goal_logs import (
    ensure_goal_metadata,
    router as goal_logs_router,
    save_goal_records,
)
from backend.schemas import (
    AssetMixResponse,
    AuthResponse,
    LoginRequest,
    ProfileInput,
    ProfileResponse,
    ReadinessResponse,
    RegisterRequest,
    RiskQuizInput,
    RiskQuizResponse,
)
from backend.calculators import (
    calculate_asset_mix,
    calculate_health_score,
    calculate_investor_type,
    calculate_money_left_after_debts,
    calculate_readiness,
    calculate_sip_future_value,
    suggest_monthly_amount,
)
from backend.investment_ideas import ideas_for_user, load_investment_ideas
from backend.chat_tools import (
    get_allocation_plan as allocation_tool,
    get_investment_ideas as ideas_tool,
    get_market_snapshot_tool,
)
from backend.llm import CoachServiceError, ask_groq
from backend.schemas import (
    AllocationPlanInput,
    AllocationPlanResponse,
    ChangePasswordRequest,
    ProfileDebtsPatch,  # Validate debt-only edits with friendly messages.
    ProfileGoalsPatch,  # Validate goal-only edits with friendly messages.
    InvestmentCapacityPatch,  # Validate monthly amount and income stability edits.
    ProjectionInput,
    ChatRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks once, then keep the app available for requests."""
    run_calculator_tests_before_startup()
    yield


app = FastAPI(
    title="ArthMitra",
    description="An educational investment learning and planning assistant.",
    lifespan=lifespan,
)
app.include_router(plan_router)
app.include_router(goal_logs_router)
app.include_router(report_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# A small login counter limits repeated password attempts in one running server.
login_attempts: dict[str, deque[float]] = {}
chat_attempts: dict[int, deque[float]] = {}


def is_login_allowed(email: str) -> bool:
    """Return whether this email has fewer than five attempts in one minute."""
    now = time.time()
    attempts = login_attempts.setdefault(email, deque())
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 5:
        return False
    attempts.append(now)
    return True


def is_chat_allowed(user_id: int) -> bool:
    """Allow up to twenty coach questions per user in one minute."""
    now = time.time()
    attempts = chat_attempts.setdefault(user_id, deque())
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 20:
        return False
    attempts.append(now)
    return True


def run_calculator_tests_before_startup() -> None:
    """Run calculator tests first so bad money maths cannot start the app."""
    if not os.getenv("VERCEL"):
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "backend/tests/test_calculators.py"],
            check=False,
        )
        if test_result.returncode != 0:
            raise RuntimeError("ArthMitra calculator tests failed. The app will not start.")
    # SQLAlchemy creates the table definitions once before the API accepts requests.
    Base.metadata.create_all(bind=engine)
    # Existing local SQLite databases need new report fields when the app upgrades.
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(engine).get_columns("profiles")}
        if "risk_answers" not in columns:
            connection.execute(
                text("ALTER TABLE profiles ADD COLUMN risk_answers JSON NOT NULL DEFAULT '[]'")
            )
        if "investor_type" not in columns:
            connection.execute(
                text("ALTER TABLE profiles ADD COLUMN investor_type VARCHAR(20)")
            )
        if "income_stability" not in columns:
            connection.execute(text(
                "ALTER TABLE profiles ADD COLUMN income_stability VARCHAR(30) NOT NULL DEFAULT 'steady'"
            ))
        if "wanted_monthly_amount" not in columns:
            connection.execute(text(
                "ALTER TABLE profiles ADD COLUMN wanted_monthly_amount VARCHAR(30)"
            ))
        user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
        if "onboarding_step" not in user_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN onboarding_step INTEGER NOT NULL DEFAULT 0")
            )
            connection.execute(text(
                "UPDATE users SET onboarding_step = CASE "
                "WHEN EXISTS (SELECT 1 FROM profiles p WHERE p.user_id = users.id "
                "AND p.investor_type IS NOT NULL) THEN 2 "
                "WHEN EXISTS (SELECT 1 FROM profiles p WHERE p.user_id = users.id "
                "AND p.income IS NOT NULL) THEN 1 ELSE 0 END"
            ))
        for column_name in (
            "money_details_completed_at",
            "risk_quiz_completed_at",
            "choices_completed_at",
            "plan_review_completed_at",
        ):
            if column_name not in user_columns:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {column_name} DATETIME")
                )
        connection.execute(text(
            "UPDATE users SET money_details_completed_at = "
            "(SELECT p.updated_at FROM profiles p WHERE p.user_id = users.id AND p.income IS NOT NULL) "
            "WHERE money_details_completed_at IS NULL"
        ))
        connection.execute(text(
            "UPDATE users SET risk_quiz_completed_at = "
            "(SELECT p.updated_at FROM profiles p WHERE p.user_id = users.id AND p.investor_type IS NOT NULL) "
            "WHERE risk_quiz_completed_at IS NULL"
        ))
        connection.execute(text(
            "UPDATE users SET choices_completed_at = "
            "(SELECT p.updated_at FROM investment_plans p WHERE p.user_id = users.id) "
            "WHERE choices_completed_at IS NULL"
        ))
        connection.execute(text(
            "UPDATE users SET plan_review_completed_at = created_at "
            "WHERE plan_review_completed_at IS NULL AND onboarding_step >= 4"
        ))
        plan_columns = {
            column["name"]
            for column in inspect(engine).get_columns("investment_plans")
        }
        if "tax_saving_80c" not in plan_columns:
            connection.execute(text(
                "ALTER TABLE investment_plans "
                "ADD COLUMN tax_saving_80c BOOLEAN NOT NULL DEFAULT 0"
            ))


def invalidate_saved_analysis(db: Session, user_id: int) -> None:
    """Mark a saved review out of date after money or risk details change."""
    plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user_id).first()
    if plan is not None:
        plan.analysis = None
        plan.is_stale = True


def profile_section_update_result(  # Refresh calculations without changing other profile sections.
    profile: Profile,  # Use the profile after its goals or debts were replaced.
    user: User,  # Keep the authenticated user's onboarding record.
    db: Session,  # Save the profile and analysis in one transaction.
) -> dict[str, object]:  # Return refreshed values for the page.
    """Recalculate the user's numbers without changing onboarding progress."""  # Explain what this helper preserves.
    if profile.income is None:  # Check that calculations have monthly income.
        raise HTTPException(status_code=409, detail="Add your money details before editing goals or debts.")  # Give a useful next step.
    readiness_result = calculate_readiness(  # Refresh readiness with saved profile values.
        profile.income,  # Use the unchanged monthly income.
        profile.expenses or "0",  # Use the saved monthly expenses.
        profile.savings or "0",  # Use the saved savings.
        profile.debts or [],  # Use the edited debt list.
    )  # Finish refreshing readiness.
    health_result = calculate_health_score(  # Refresh health and goal progress.
        profile.income,  # Use the unchanged monthly income.
        profile.expenses or "0",  # Use the saved monthly expenses.
        profile.savings or "0",  # Use the saved savings.
        profile.debts or [],  # Use the edited debt list.
        profile.goals or [],  # Use the edited goal list.
    )  # Finish refreshing the health score.
    money_left = calculate_money_left_after_debts(  # Refresh monthly money left.
        profile.income,  # Use the unchanged monthly income.
        profile.expenses or "0",  # Use the saved monthly expenses.
        profile.debts or [],  # Subtract the edited debt payments.
    )  # Finish refreshing the monthly balance.
    invalidate_saved_analysis(db, user.id)  # Mark any old plan review for another check.
    saved_plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user.id).first()  # Find the saved plan, if one exists.
    plan_analysis = None  # Keep the analysis empty when there is no plan to recalculate.
    if saved_plan is not None and profile.investor_type:  # Recalculate a plan when its profile is complete.
        analysis_user = {  # Give the analyzer the freshly saved profile values.
            "income": profile.income,  # Use the saved monthly income.
            "expenses": profile.expenses or "0",  # Use the saved monthly expenses.
            "savings": profile.savings or "0",  # Use the saved savings.
            "debts": profile.debts or [],  # Use only the newly saved debts.
            "goals": profile.goals or [],  # Use only the newly saved goals.
            "investor_type": profile.investor_type,  # Keep the user's saved risk type.
        }  # Finish the analysis profile.
        plan_analysis = analyze_plan(  # Recompute goal chances and plan checks.
            analysis_user,  # Analyze the latest profile values.
            {"monthly_amount": saved_plan.monthly_amount, "parts": saved_plan.parts or []},  # Keep the saved plan allocation.
        )  # Finish refreshing the saved plan analysis.
        saved_plan.analysis = stringify_decimals(plan_analysis)  # Store the fresh exact results.
        saved_plan.is_stale = True  # Keep the re-check banner until the user reviews the plan.
    db.commit()  # Save the edited section and refreshed plan analysis together.
    db.refresh(profile)  # Read the committed profile values for the response.
    record_progress_snapshot(user, db)  # Save the updated financial facts for the report.
    return {  # Return updated data for the page to refresh.
        "profile": profile_response(profile, user).model_dump(mode="json"),  # Return the complete unchanged-plus-updated profile.
        "readiness": stringify_decimals(readiness_result),  # Return the refreshed readiness checks.
        "health_score": stringify_decimals(health_result),  # Return the refreshed health and goal progress.
        "money_left_monthly": str(money_left),  # Return the refreshed monthly balance.
        "plan_analysis": stringify_decimals(plan_analysis) if plan_analysis is not None else None,  # Return the refreshed plan review.
        "plan_changed": saved_plan is not None,  # Tell the page whether a re-check banner is needed.
        "plan_notice": "Your goals/debts changed. Re-check your plan." if saved_plan is not None else None,  # Show the requested plan reminder.
        "message": "Saved. Your numbers are updated.",  # Confirm the save in simple English.
    }  # Finish the refreshed response.


def require_onboarding_complete(user: User) -> None:
    """Keep dashboard-only information behind the completed setup flow."""
    if user.onboarding_step < 4:
        raise HTTPException(status_code=409, detail="onboarding_incomplete")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Return a simple status so the setup can be checked.

    It takes no input and returns a status value and a short message.
    """
    return {
        "status": "ok",
        "message": "ArthMitra backend is ready.",
    }


@app.get("/dashboard")
def dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return the latest backend-calculated dashboard values saved in SQLite."""
    profile = get_user_profile(user, db)
    return build_dashboard_result(user, profile, db)


@app.get("/market-snapshot")
def read_market_snapshot(user: User = Depends(get_current_user)) -> dict[str, object]:
    """Return the cached public market snapshot and its source details."""
    return get_market_snapshot_tool()


@app.post("/market-snapshot/refresh")
def refresh_market_snapshot(user: User = Depends(get_current_user)) -> dict[str, object]:
    """Refresh public market figures and use saved values if any source fails."""
    return get_market_snapshot_tool(refresh=True)


@app.post("/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register an account and return a short-lived login token."""
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account already uses this email.")
    user = User(email=request.email, password_hash=hash_password(request.password))
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, debts=[], goals=[]))
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(user.id))


@app.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Validate an email and password, with simple repeated-login protection."""
    email = request.email.strip().lower()
    if not is_login_allowed(email):
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait a minute.")
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    return AuthResponse(access_token=create_access_token(user.id))


def profile_response(profile: Profile, user: User | None = None) -> ProfileResponse:
    """Convert a database profile into a safe JSON response."""
    return ProfileResponse(
        income=profile.income,
        expenses=profile.expenses,
        savings=profile.savings,
        debts=profile.debts or [],
        goals=profile.goals or [],
        email=user.email if user else None,
        investor_type=profile.investor_type,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
        income_stability=profile.income_stability or "steady",
        wanted_monthly_amount=profile.wanted_monthly_amount,
    )


def _monthly_amount_profile_data(
    profile: Profile,
    db: Session,
    income_stability: str | None = None,
    wanted_monthly_amount: Decimal | None = None,
) -> dict[str, object]:
    """Build the calculator input from this user's saved profile and chosen plan."""
    plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == profile.user_id).first()
    catalog = {idea["id"]: idea for idea in load_investment_ideas()}
    plan_parts = []
    if plan is not None:
        for saved_part in plan.parts or []:
            share = Decimal(str(saved_part.get("share", "0")))
            if share <= Decimal("0"):  # Ignore saved zero-share ideas in the goal calculation.
                continue
            idea = catalog.get(str(saved_part.get("idea_id", "")))
            if idea is None:  # Do not silently guess when a saved investment is missing.
                raise HTTPException(
                    status_code=409,
                    detail="A saved plan idea is no longer available. Please edit your plan.",
                )
            plan_parts.append({
                "share": share,
                "expected_return_mid": Decimal(str(idea["expected_return_mid"])),
            })
    return {
        "income": profile.income or "0",
        "expenses": profile.expenses or "0",
        "savings": profile.savings or "0",
        "debts": profile.debts or [],
        "goals": profile.goals or [],
        "income_stability": income_stability or profile.income_stability or "steady",
        "wanted_monthly_amount": (
            wanted_monthly_amount
            if wanted_monthly_amount is not None
            else profile.wanted_monthly_amount
        ),
        "monthly_amount": plan.monthly_amount if plan is not None else None,
        "plan_parts": plan_parts,
    }


def _smart_monthly_amount_for_profile(
    profile: Profile,
    db: Session,
    income_stability: str | None = None,
    wanted_monthly_amount: Decimal | None = None,
) -> dict[str, object]:
    """Calculate the monthly suggestion from the current saved profile and plan."""
    return suggest_monthly_amount(
        _monthly_amount_profile_data(profile, db, income_stability, wanted_monthly_amount)
    )


@app.get("/profile", response_model=ProfileResponse)
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Return the signed-in user's saved financial profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id, debts=[], goals=[], income=None, expenses=None, savings=None)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    ensure_goal_metadata(profile, user)
    db.commit()
    return profile_response(profile, user)


@app.get("/smart-monthly-amount")  # Return a fresh amount comparison for this signed-in user.
def get_smart_monthly_amount(  # Recalculate whenever profile or plan values change.
    user: User = Depends(get_current_user),  # Keep the suggestion private to the account owner.
    db: Session = Depends(get_db),  # Read the profile and plan from this request's session.
) -> dict[str, object]:  # Return exact calculator values and their local calculation time.
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()  # Find only the caller's profile.
    if profile is None:  # Return a friendly setup message if no profile exists.
        raise HTTPException(status_code=404, detail="Add your money details to get a monthly amount suggestion.")  # Explain what to do next.
    return _smart_monthly_amount_for_profile(profile, db)  # Recalculate from current saved data.


@app.post("/smart-monthly-amount/preview")  # Preview edits without changing saved profile data.
def preview_smart_monthly_amount(  # Use form values for one temporary calculation.
    request: InvestmentCapacityPatch,  # Validate the temporary choices before calculation.
    user: User = Depends(get_current_user),  # Keep the preview private to the signed-in user.
    db: Session = Depends(get_db),  # Read only this user's current profile and plan.
) -> dict[str, object]:  # Return a fresh preview without saving it.
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()  # Find only this user's profile.
    if profile is None:  # Require money details for an amount preview.
        raise HTTPException(status_code=404, detail="Save your money details before setting a monthly amount.")  # Explain what to do next.
    return _smart_monthly_amount_for_profile(  # Calculate using form choices without storing them.
        profile,
        db,
        request.income_stability,
        request.wanted_monthly_amount,
    )  # Finish the temporary preview response.


@app.put("/profile", response_model=ProfileResponse)
def put_profile(
    request: ProfileInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Validate and save the signed-in user's financial profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    profile.income = str(request.income)
    profile.expenses = str(request.expenses)
    profile.savings = str(request.savings)
    if request.income_stability is not None:  # Keep a saved stability choice during a full money edit.
        profile.income_stability = request.income_stability  # Save the user's income pattern.
    if request.wanted_monthly_amount is not None:  # Keep a saved monthly preference when the form includes it.
        profile.wanted_monthly_amount = str(request.wanted_monthly_amount)  # Store the exact amount as text.
    profile.debts = [debt.model_dump(mode="json") for debt in request.debts]
    save_goal_records(profile, user, request.goals)
    if user.onboarding_step < 4:
        user.onboarding_step = max(user.onboarding_step, 1)
    if user.money_details_completed_at is None:
        user.money_details_completed_at = datetime.now(timezone.utc)
    invalidate_saved_analysis(db, user.id)
    db.commit()
    db.refresh(profile)
    record_progress_snapshot(user, db)
    return profile_response(profile, user)


@app.patch("/profile/investment-capacity")  # Update only the preferred SIP and income pattern.
def patch_investment_capacity(  # Save the two smart-amount choices without replacing other details.
    request: InvestmentCapacityPatch,  # Validate each optional value before saving it.
    user: User = Depends(get_current_user),  # Use only the signed-in user's account.
    db: Session = Depends(get_db),  # Save through the normal request database.
) -> dict[str, object]:  # Return the new profile and freshly calculated suggestion.
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()  # Find this user's profile.
    if profile is None:  # Explain when money details have not been saved yet.
        raise HTTPException(status_code=404, detail="Save your money details before setting a monthly amount.")  # Give a useful next step.
    if not request.model_fields_set:  # Do not accept an empty patch as a successful save.
        raise HTTPException(status_code=422, detail="Choose an income pattern or monthly amount.")  # Explain what the form needs.
    if request.income_stability is not None:  # Update the stability only when the user sent it.
        profile.income_stability = request.income_stability  # Keep the new stability choice.
    if request.wanted_monthly_amount is not None:  # Keep zero as a valid preferred amount.
        profile.wanted_monthly_amount = str(request.wanted_monthly_amount)  # Store the exact amount.
    invalidate_saved_analysis(db, user.id)  # Mark saved analysis stale when the preference changes.
    db.commit()  # Save only the two smart-amount fields.
    db.refresh(profile)  # Read the saved profile values.
    record_progress_snapshot(user, db)  # Keep the report history current after a profile edit.
    return {  # Return saved values and the new Decimal calculation.
        "message": "Saved. Your monthly amount suggestion is updated.",  # Confirm the save in simple English.
        "profile": profile_response(profile, user).model_dump(mode="json"),  # Return this user's profile only.
        "suggestion": _smart_monthly_amount_for_profile(profile, db),  # Recalculate with saved values.
    }  # Finish the section-only update response.


@app.patch("/profile/goals")  # Update goals without changing other profile details.
def patch_profile_goals(  # Save only the goals list supplied by the user.
    request: ProfileGoalsPatch,  # Validate every goal before changing the profile.
    user: User = Depends(get_current_user),  # Use the signed-in user only.
    db: Session = Depends(get_db),  # Use the request's database session.
) -> dict[str, object]:  # Return the updated profile and recalculated values.
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()  # Find this user's profile.
    if profile is None:  # Handle accounts without a profile row.
        raise HTTPException(status_code=404, detail="Save your money details before editing goals.")  # Explain how to continue.
    save_goal_records(profile, user, request.goals)  # Keep goal IDs while replacing only the goals list.
    return profile_section_update_result(profile, user, db)  # Refresh all dependent calculations.


@app.patch("/profile/debts")  # Update debts without changing other profile details.
def patch_profile_debts(  # Save only the debts list supplied by the user.
    request: ProfileDebtsPatch,  # Validate every debt before changing the profile.
    user: User = Depends(get_current_user),  # Use the signed-in user only.
    db: Session = Depends(get_db),  # Use the request's database session.
) -> dict[str, object]:  # Return the updated profile and recalculated values.
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()  # Find this user's profile.
    if profile is None:  # Handle accounts without a profile row.
        raise HTTPException(status_code=404, detail="Save your money details before editing debts.")  # Explain how to continue.
    profile.debts = [debt.model_dump(mode="json") for debt in request.debts]  # Replace debts and leave every other field untouched.
    return profile_section_update_result(profile, user, db)  # Refresh all dependent calculations.


@app.post("/risk-quiz", response_model=RiskQuizResponse)
def risk_quiz(
    request: RiskQuizInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskQuizResponse:
    """Score seven answers and save the user's conservative, balanced or aggressive type."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None or profile.income is None:
        raise HTTPException(
            status_code=409,
            detail="Save your money details before taking the risk quiz.",
        )
    investor_type, score, explanation = calculate_investor_type(request.answers)
    profile.risk_answers = request.answers
    profile.investor_type = investor_type
    if user.onboarding_step < 4:
        user.onboarding_step = max(user.onboarding_step, 2)
    if user.risk_quiz_completed_at is None:
        user.risk_quiz_completed_at = datetime.now(timezone.utc)
    invalidate_saved_analysis(db, user.id)
    db.commit()
    record_progress_snapshot(user, db)
    return RiskQuizResponse(
        investor_type=investor_type,
        score=score,
        explanation=explanation,
    )


@app.get("/readiness", response_model=ReadinessResponse)
def readiness(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    """Check emergency savings, costly debt and savings rate for a ready-to-invest decision."""
    require_onboarding_complete(user)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None or profile.income is None:
        return ReadinessResponse(
            ready=False,
            emergency_fund_months="0.00",
            has_high_interest_debt=False,
            savings_rate="0.00",
            checks=[
                {"name": "Emergency fund", "passed": False, "detail": "Add your monthly expenses and savings."},
                {"name": "High-interest debt", "passed": False, "detail": "Add your debts to check their rates."},
                {"name": "Savings rate", "passed": False, "detail": "Add your income and expenses."},
            ],
            fix_plan=["Add your money details to check if you are ready."],
        )
    result = calculate_readiness(
        profile.income,
        profile.expenses or "0",
        profile.savings or "0",
        profile.debts or [],
    )
    return ReadinessResponse(
        ready=bool(result["ready"]),
        emergency_fund_months=str(result["emergency_fund_months"]),
        has_high_interest_debt=bool(result["has_high_interest_debt"]),
        savings_rate=str(result["savings_rate"]),
        checks=list(result["checks"]),
        fix_plan=list(result["fix_plan"]),
    )


@app.get("/asset-mix", response_model=AssetMixResponse)
def asset_mix(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetMixResponse:
    """Return a suggested equity, debt, gold and cash mix for the saved investor type."""
    require_onboarding_complete(user)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    investor_type = profile.investor_type if profile and profile.investor_type else "balanced"
    result = calculate_asset_mix(investor_type)
    reasons = {
        "equity": "Equity means company shares that can grow over long periods but can fall too.",
        "debt": "Debt means lending to banks or governments for steadier, lower-risk income.",
        "gold": "Gold is a diversifier that may help when other investments struggle.",
        "fd_cash": "FD and cash are familiar, easy-to-use choices for safety and near-term needs.",
    }
    return AssetMixResponse(
        investor_type=str(result["investor_type"]),
        equity=int(result["equity"]),
        debt=int(result["debt"]),
        gold=int(result["gold"]),
        fd_cash=int(result["fd_cash"]),
        expected_return_range=str(result["expected_return_range"]),
        reasons=reasons,
    )


def build_idea_user(user: User, profile: Profile) -> dict[str, object]:
    """Make the saved profile details needed for idea matching."""
    readiness = calculate_readiness(
        profile.income or "1",
        profile.expenses or "0",
        profile.savings or "0",
        profile.debts or [],
    )
    emergency_months = readiness["emergency_fund_months"]
    high_interest_debt = bool(readiness["has_high_interest_debt"])
    has_profile_data = bool(profile.income)
    no_monthly_expenses = has_profile_data and Decimal(profile.expenses or "0") == 0
    ready = has_profile_data and (no_monthly_expenses or emergency_months >= 3) and not high_interest_debt
    monthly_amount = calculate_money_left_after_debts(
        profile.income or "1",
        profile.expenses or "0",
        profile.debts or [],
    )
    return {
        "email": user.email,
        "investor_type": profile.investor_type or "balanced",
        "goals": profile.goals or [],
        "monthly_amount": monthly_amount,
        "emergency_fund_months": emergency_months,
        "no_monthly_expenses": no_monthly_expenses,
        "has_profile_data": has_profile_data,
        "has_high_interest_debt": high_interest_debt,
        "readiness": readiness,
        "ready": ready,
    }


def get_user_profile(user: User, db: Session) -> Profile:
    """Find a user's saved profile or create its empty starting record."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id, debts=[], goals=[], risk_answers=[])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@app.get("/investment-ideas")
def get_investment_ideas(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return all ideas sorted by match score, including locked ideas and reasons."""
    profile = get_user_profile(user, db)
    result = ideas_tool(build_idea_user(user, profile))
    matched_ideas = result["ideas"]
    return {
        "ideas": matched_ideas,
        "top_picks": result["top_picks"],
        "disclaimer": "Educational guidance only. Not licensed financial advice. Investments carry risk. Returns are not guaranteed.",
    }


@app.get("/investment-ideas/{idea_id}")
def get_investment_idea(
    idea_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return one idea's full learning details and its personal match."""
    idea = next((item for item in load_investment_ideas() if item["id"] == idea_id), None)
    if idea is None:
        raise HTTPException(status_code=404, detail="We could not find that investment idea.")
    profile = get_user_profile(user, db)
    return next(
        matched for matched in ideas_for_user(build_idea_user(user, profile))
        if matched["id"] == idea_id
    )


@app.post("/allocation-plan", response_model=AllocationPlanResponse)
def post_allocation_plan(
    request: AllocationPlanInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllocationPlanResponse:
    """Split a monthly amount into seven jars or explain which money basics need work."""
    require_onboarding_complete(user)
    profile = get_user_profile(user, db)
    context = build_idea_user(user, profile)
    investor_type = str(context["investor_type"])
    plan = allocation_tool(request.monthly_amount, context)
    if not plan["ready"]:
        return AllocationPlanResponse(
            ready=False,
            monthly_amount=str(request.monthly_amount),
            investor_type=investor_type,
            fix_plan=list(plan["fix_plan"]),
        )

    items = []
    for item in plan["items"]:
        growth = {
            years: {level: str(value) for level, value in values.items()}
            for years, values in item["growth"].items()
        }
        items.append({
            **item,
            "monthly_amount": str(item["monthly_amount"]),
            "growth": growth,
        })
    return AllocationPlanResponse(
        ready=True,
        monthly_amount=str(plan["monthly_amount"]),
        investor_type=investor_type,
        items=items,
        totals={ # Return the values computed from the Decimal rows.
            "monthly": str(plan["totals"]["monthly"]), # Keep the monthly sum exact in JSON.
            "five_year_middle": str(plan["totals"]["five_year_middle"]), # Keep the five-year sum exact.
            "ten_year_middle": str(plan["totals"]["ten_year_middle"]), # Keep the ten-year sum exact.
        }, # Send all three totals with the plan.
        total=str(plan["total"]),
        summary=str(plan["summary"]),
        label=str(plan["label"]),
    )


@app.get("/health-score")
def health_score(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return a simple money-health score and the two weakest areas."""
    require_onboarding_complete(user)
    profile = get_user_profile(user, db)
    if not profile.income:
        return {
            "score": 0,
            "factors": {},
            "top_hurts": ["Add your money details to see your health score."],
            "emergency_fund_months": "0.00",
            "monthly_left": "0.00",
            "suggested_monthly_amount": "0.00",
            "debt_to_income_ratio": "0.00",
            "goals": [],
        }
    result = calculate_health_score(
        profile.income,
        profile.expenses or "0",
        profile.savings or "0",
        profile.debts or [],
        profile.goals or [],
    )
    return {
        "score": result["score"],
        "factors": {name: str(value) for name, value in result["factors"].items()},
        "top_hurts": result["top_hurts"],
        "emergency_fund_months": str(result["emergency_fund_months"]),
        "no_monthly_expenses": Decimal(profile.expenses or "0") == 0,
        "monthly_left": str(result["monthly_left"]),
        "suggested_monthly_amount": str(result["suggested_monthly_amount"]),
        "debt_to_income_ratio": str(result["debt_to_income_ratio"]),
        "goals": [
            {
                **goal,
                "amount": str(goal["amount"]),
                "progress_percent": str(goal["progress_percent"]),
            }
            for goal in result["goals"]
        ],
    }


@app.post("/projection")
def projection(
    request: ProjectionInput,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Show an estimated SIP result for a monthly amount, rate and time."""
    require_onboarding_complete(user)
    future_value = calculate_sip_future_value(
        request.monthly_amount,
        request.annual_rate,
        request.years,
    )
    return {
        "monthly_amount": str(request.monthly_amount),
        "annual_rate": str(request.annual_rate),
        "years": str(request.years),
        "future_value": str(future_value),
        "label": "Expected, not guaranteed",
    }


@app.post("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Change the signed-in user's password after checking the old password."""
    if not verify_password(request.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is not correct.")
    if request.old_password == request.new_password:
        raise HTTPException(status_code=400, detail="Choose a new password different from the old one.")
    user.password_hash = hash_password(request.new_password)
    db.commit()
    return {"message": "Your password was changed."}


@app.post("/auth/logout")
def logout(user: User = Depends(get_current_user)) -> dict[str, str]:
    """Confirm logout; the browser completes logout by deleting its saved token."""
    return {"message": "You are logged out. Please remove your saved sign-in token."}


def stringify_decimals(value):
    """Turn Decimal results into safe, exact JSON strings for the coach."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: stringify_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stringify_decimals(item) for item in value]
    return value


@app.post("/chat")
def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Send every question to Groq with this user's saved financial context."""
    if not is_chat_allowed(user.id):
        raise HTTPException(status_code=429, detail="Too many questions. Please try again in a minute.")
    profile = get_user_profile(user, db)
    dashboard_record = (
        db.query(DashboardResult)
        .filter(DashboardResult.user_id == user.id)
        .first()
    )
    dashboard_data = dashboard_record.result if dashboard_record is not None else None
    plan = (
        db.query(InvestmentPlan)
        .filter(InvestmentPlan.user_id == user.id)
        .first()
    )
    latest_snapshot = (
        db.query(ProgressSnapshot)
        .filter(ProgressSnapshot.user_id == user.id)
        .order_by(ProgressSnapshot.created_at.desc(), ProgressSnapshot.id.desc())
        .first()
    )
    active_logs = (
        db.query(InvestmentLog.amount)
        .filter(
            InvestmentLog.user_id == user.id,
            InvestmentLog.deleted_at.is_(None),
        )
        .all()
    )
    value_snapshots = (
        db.query(GoalValueSnapshot)
        .filter(GoalValueSnapshot.user_id == user.id)
        .order_by(GoalValueSnapshot.taken_at.asc(), GoalValueSnapshot.id.asc())
        .all()
    )
    snapshots_by_goal: dict[str, list[GoalValueSnapshot]] = {}
    for snapshot in value_snapshots:
        snapshots_by_goal.setdefault(snapshot.goal_id, []).append(snapshot)
    saved_value_history = [
        {
            "goal_id": goal_id,
            "snapshot_count": len(snapshots),
            "first": {
                "value": str(snapshots[0].value),
                "taken_at": str(snapshots[0].taken_at),
            },
            "latest": {
                "value": str(snapshots[-1].value),
                "taken_at": str(snapshots[-1].taken_at),
            },
            "past_growth_available": len(snapshots) >= 2,
        }
        for goal_id, snapshots in snapshots_by_goal.items()
    ]
    has_growth_history = any(
        item["past_growth_available"] for item in saved_value_history
    )
    context = {
        "saved_profile": {
            "income": profile.income,
            "expenses": profile.expenses,
            "savings": profile.savings,
            "goals": profile.goals or [],
            "debts": profile.debts or [],
            "income_stability": profile.income_stability,
            "wanted_monthly_amount": profile.wanted_monthly_amount,
        },
        "saved_plan": (
            {
                "monthly_amount": plan.monthly_amount,
                "parts": plan.parts or [],
                "analysis": plan.analysis,
                "is_stale": plan.is_stale,
            }
            if plan is not None
            else None
        ),
        "latest_calculator_results": {
            "dashboard": dashboard_data,
            "progress_snapshot": (
                {
                    "calculated_at": str(latest_snapshot.created_at),
                    "health_score": latest_snapshot.health_score,
                    "plan_score": latest_snapshot.plan_score,
                    "monthly_income": latest_snapshot.monthly_income,
                    "monthly_expenses": latest_snapshot.monthly_expenses,
                    "money_left_monthly": latest_snapshot.money_left_monthly,
                    "total_invested": latest_snapshot.total_invested,
                    "value_today": latest_snapshot.value_today,
                    "goal_chances": latest_snapshot.goal_chances,
                }
                if latest_snapshot is not None
                else None
            ),
        },
        "investment_history": {
            "active_log_count": len(active_logs),
            "total_logged": str(sum((row[0] for row in active_logs), Decimal("0"))),
            "saved_value_history": saved_value_history,
            "past_growth_available": has_growth_history,
            "status": (
                "Saved account-value history is available."
                if has_growth_history
                else "There are not enough saved account-value snapshots to calculate past growth."
            ),
        },
    }
    try:
        answer = ask_groq(request.question, context)
    except CoachServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"answer": answer}