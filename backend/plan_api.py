"""Save, review and track one user's investment-learning plan."""

from decimal import Decimal
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.analysis import analyze_plan
from backend.auth import get_current_user
from backend.calculators import (
    calculate_preview_amounts,
    calculate_money_left_after_debts,
    calculate_plan_growth,
    calculate_readiness,
    max_parts,
    round_money,
    split_monthly_amount,
    split_monthly_amount,
)
from backend.database import get_db
from backend.investment_ideas import (
    load_basics_jars,
    load_investment_ideas,
)
from backend.models import InvestmentPlan, Profile, User
from backend.report import record_progress_snapshot
from backend.schemas import (
    PlanConfirmInput,
    PlanFixInput,
    PlanInput,
    PlanTaskInput,
    SmartAmountSaveRequest,
)
from backend.market_data import get_market_snapshot
from backend.suggest import build_smart_suggestion
from backend.smart_amount import calculate_amount_growth


router = APIRouter()
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _profile_for_user(user: User, db: Session) -> Profile:
    """Find or create the signed-in user's profile row."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id, debts=[], goals=[], risk_answers=[])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _profile_data(profile: Profile) -> dict[str, Any]:
    """Copy the money details used by the status and plan calculations."""
    return {
        "income": profile.income or "1",
        "expenses": profile.expenses or "0",
        "savings": profile.savings or "0",
        "debts": profile.debts or [],
        "goals": profile.goals or [],
        "investor_type": profile.investor_type or "balanced",
    }


def _investment_catalog() -> dict[str, dict[str, Any]]:
    """Return every selectable idea and safe basics jar by its stable id."""
    return {
        str(item["id"]): item
        for item in load_investment_ideas() + load_basics_jars()
    }


def _readiness(profile: Profile) -> dict[str, Any]:
    """Calculate whether high-risk ideas need to stay locked for this user."""
    return calculate_readiness(
        profile.income or "1",
        profile.expenses or "0",
        profile.savings or "0",
        profile.debts or [],
    )


def _require_choices_access(user: User, profile: Profile) -> None:
    """Require saved money details and risk answers before choices can be previewed."""
    if user.onboarding_step < 2 or profile.income is None or profile.investor_type is None:
        raise HTTPException(
            status_code=409,
            detail="Finish your money details and risk quiz before choosing plan parts.",
        )


def _check_plan_parts(
    monthly_amount: object,
    parts: list[dict[str, Any]],
    profile: Profile,
    require_exact_total: bool = True,
    allow_existing_locked: bool = False,
) -> list[Decimal]:
    """Check selected ids and locks, then return exact paise-rounded part amounts."""
    if len({part["idea_id"] for part in parts}) != len(parts):
        raise ValueError("Choose each idea only once.")
    amount = Decimal(str(monthly_amount))
    allowed_count = max_parts(max(ZERO, amount))
    if len(parts) > allowed_count:
        raise ValueError(
            f"Choose no more than {allowed_count} part"
            f"{'' if allowed_count == 1 else 's'} for this monthly amount."
        )
    catalog = _investment_catalog()
    readiness = _readiness(profile)
    emergency_ready = (
        Decimal(str(profile.expenses or "0")) == ZERO
        or Decimal(str(readiness["emergency_fund_months"])) >= Decimal("3")
    )
    has_high_interest_debt = bool(readiness["has_high_interest_debt"])
    shares = []
    for part in parts:
        idea_id = str(part["idea_id"])
        idea = catalog.get(idea_id)
        if idea is None:
            raise ValueError("Choose an investment idea from the list.")
        is_special = idea_id in {"emergency-fund", "debt-payoff"}
        if (
            not is_special
            and not allow_existing_locked
            and not emergency_ready
            and (Decimal(str(readiness["emergency_fund_months"])) < 3 or has_high_interest_debt)
            and int(idea["risk_level"]) >= 3
        ):
            raise ValueError(f"{idea['name']} is locked. Fix basics first.")
        shares.append(part["share"])
    if require_exact_total:
        amounts = split_monthly_amount(monthly_amount, shares)
        if any(Decimal(str(share)) < Decimal("10") for share in shares):
            raise ValueError("Every part must be at least 10% of the monthly amount.")
        if any(amount < Decimal("500") for amount in amounts):
            raise ValueError("Every part must be at least ₹500.")
        return amounts
    return calculate_preview_amounts(monthly_amount, shares)


def _get_plan(user: User, db: Session) -> InvestmentPlan | None:
    """Find the user's current saved plan, if one exists."""
    return db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user.id).first()


def _make_tasks(parts: list[dict[str, Any]], old_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create one first-month task per part and keep progress for unchanged tasks."""
    old_status = {task["id"]: bool(task.get("completed")) for task in old_tasks}
    ideas = _investment_catalog()
    basics_tasks = {
        "emergency-fund": "Put this month's emergency-fund amount in an easy-to-reach place.",
        "debt-payoff": "Pay this month's extra amount toward your highest-interest debt.",
    }
    ordered = sorted(
        enumerate(parts),
        key=lambda item: (
            0 if item[1]["idea_id"] in {"emergency-fund", "debt-payoff"} else 1,
            item[0],
        ),
    )
    tasks = []
    for position, (_, part) in enumerate(ordered, start=1):
        idea_id = str(part["idea_id"])
        idea = ideas[idea_id]
        task_id = f"task-{idea_id}"
        description = basics_tasks.get(
            idea_id,
            (idea.get("how_to_start") or ["Learn how to open this account."])[0],
        )
        tasks.append({
            "id": task_id,
            "idea_id": idea_id,
            "title": f"Part {position}: {description}",
            "completed": old_status.get(task_id, False),
        })
    return tasks


def _plan_response(plan: InvestmentPlan | None) -> dict[str, Any]:
    """Return a consistent empty or saved plan response."""
    if plan is None:
        return {
            "exists": False,
            "monthly_amount": None,
            "parts": [],
            "tax_saving_80c": False,
            "analysis": None,
            "tasks": [],
            "is_stale": True,
        }
    return {
        "exists": True,
        "monthly_amount": plan.monthly_amount,
        "parts": plan.parts or [],
        "tax_saving_80c": bool(plan.tax_saving_80c),
        "analysis": plan.analysis,
        "tasks": plan.tasks or [],
        "is_stale": plan.is_stale,
    }


def _json_safe(value: Any) -> Any:
    """Convert exact Decimal values recursively for API and SQLite JSON responses."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _save_plan(
    user: User,
    db: Session,
    monthly_amount: object,
    parts: list[dict[str, Any]],
    tax_saving_80c: bool | None = None,
) -> InvestmentPlan:
    """Save plan choices, mark old analysis stale and preserve matching tasks."""
    profile = _profile_for_user(user, db)
    part_amounts = _check_plan_parts(monthly_amount, parts, profile)
    normalized_amount = round_money(monthly_amount)
    if sum(part_amounts, ZERO) != normalized_amount:
        raise ValueError("The part amounts did not add up. Please try your plan again.")
    saved = _get_plan(user, db)
    old_tasks = list(saved.tasks or []) if saved else []
    if saved is None:
        saved = InvestmentPlan(
            user_id=user.id,
            monthly_amount=str(monthly_amount),
            parts=[],
            tax_saving_80c=False,
            tasks=[],
            is_stale=True,
        )
        db.add(saved)
    saved.monthly_amount = str(normalized_amount)
    profile.wanted_monthly_amount = str(normalized_amount)  # Keep the saved plan amount as the user's current choice.
    if tax_saving_80c is not None:
        saved.tax_saving_80c = tax_saving_80c
    saved.parts = [
        {"idea_id": str(part["idea_id"]), "share": str(Decimal(str(part["share"])))}
        for part in parts
    ]
    saved.analysis = None
    saved.tasks = _make_tasks(saved.parts, old_tasks)
    saved.is_stale = True
    if user.onboarding_step < 3:
        user.onboarding_step = 3
    if user.choices_completed_at is None:
        user.choices_completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(saved)
    record_progress_snapshot(user, db)
    return saved


def _analysis_context(user: User, db: Session) -> tuple[Profile, InvestmentPlan]:
    """Load the user's details and saved plan before any review or comparison."""
    profile = _profile_for_user(user, db)
    plan = _get_plan(user, db)
    if user.onboarding_step < 3 or plan is None:
        raise HTTPException(
            status_code=409,
            detail="Save your investment choices before reviewing a plan.",
        )
    if profile.income is None or profile.investor_type is None:
        raise HTTPException(
            status_code=409,
            detail="Finish your money details and risk quiz before reviewing a plan.",
        )
    return profile, plan


def _analyze_and_save(user: User, db: Session) -> dict[str, Any]:
    """Run fresh plan checks and store the result with exact Decimal values as strings."""
    profile, plan = _analysis_context(user, db)
    result = analyze_plan(_profile_data(profile), {
        "monthly_amount": plan.monthly_amount,
        "parts": plan.parts or [],
    })

    plan.analysis = _json_safe(result)
    plan.is_stale = False
    db.commit()
    return plan.analysis


def _suggestion(
    profile: Profile,
    monthly_amount: object,
    tax_saving_80c: bool = False,
) -> dict[str, Any]:
    """Build the sourced suggestion from this user's risk, goals and readiness."""
    return build_smart_suggestion(
        monthly_amount,
        profile.investor_type or "balanced",
        profile.goals or [],
        _readiness(profile),
        get_market_snapshot(),
        tax_saving_80c,
    )


@router.get("/onboarding/status")
def onboarding_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return saved setup progress, the next page, and the safe monthly amount."""
    profile = _profile_for_user(user, db)
    pages = {
        0: ("money-details", 2),
        1: ("retake-quiz", 3),
        2: ("investment-choices", 4),
        3: ("plan-review", 5),
        4: ("dashboard", 5),
    }
    next_page, step_number = pages.get(
        min(max(int(user.onboarding_step), 0), 4),
        ("money-details", 2),
    )
    safe_amount = None
    if profile.income is not None:
        safe_amount = calculate_money_left_after_debts(
            profile.income,
            profile.expenses or "0",
            profile.debts or [],
        )
    return {
        "onboarding_step": int(user.onboarding_step),
        "step_number": step_number,
        "next_page": next_page,
        "complete": int(user.onboarding_step) >= 4,
        "safe_monthly_amount": str(safe_amount) if safe_amount is not None else None,
        "max_parts": max_parts(max(ZERO, safe_amount or ZERO)),
    }


@router.get("/plan/suggestion")
def get_plan_suggestion(
    monthly_amount: Decimal = Query(ge=0, max_digits=16, decimal_places=2),
    tax_saving_80c: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return ArthMitra's starter split or a safe emergency/debt-first plan."""
    profile = _profile_for_user(user, db)
    _require_choices_access(user, profile)
    readiness = _readiness(profile)
    saved_plan = _get_plan(user, db)
    use_tax_saving = (
        tax_saving_80c
        if tax_saving_80c is not None
        else bool(saved_plan and saved_plan.tax_saving_80c)
    )
    try:
        suggestion = _suggestion(profile, monthly_amount, use_tax_saving)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    catalog = _investment_catalog()
    safe_amount = calculate_money_left_after_debts(
        profile.income or "1",
        profile.expenses or "0",
        profile.debts or [],
    )
    return {
        **_json_safe(suggestion),
        "parts": [
            {
                **_json_safe(part),
                "name": catalog[part["idea_id"]]["name"],
                "asset_class": catalog[part["idea_id"]]["asset_class"],
                "share": str(part["share"]),
                "monthly_amount": str(part["monthly_amount"]),
            }
            for part in suggestion["parts"]
        ],
        "basics": load_basics_jars() if not bool(readiness["ready"]) else [],
        "max_parts": max_parts(monthly_amount),
        "safe_monthly_amount": str(safe_amount) if profile.income is not None else None,
        "amount_over_safe": profile.income is not None and monthly_amount > safe_amount,
        "safe_amount_negative": safe_amount <= ZERO,
        "ready_for_investment": bool(readiness["ready"]),
    }


@router.post("/plan/preview")
def preview_plan(
    request: PlanInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Check a live slider split and return each part's exact monthly amount."""
    profile = _profile_for_user(user, db)
    _require_choices_access(user, profile)
    parts = [part.model_dump() for part in request.parts]
    try:
        amounts = _check_plan_parts(
            request.monthly_amount,
            parts,
            profile,
            require_exact_total=False,
            allow_existing_locked=user.onboarding_step >= 4,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    catalog = _investment_catalog()
    return {
        "total": str(round_money(request.monthly_amount)),
        "parts": [
            {
                **part,
                "name": catalog[part["idea_id"]]["name"],
                "asset_class": catalog[part["idea_id"]]["asset_class"],
                "monthly_amount": str(amount),
                "minimum_to_start": str(max(
                    Decimal("500"),
                    Decimal(str(catalog[part["idea_id"]]["minimum_to_start"])),
                )),
                "below_minimum": (
                    amount < max(
                        Decimal("500"),
                        Decimal(str(catalog[part["idea_id"]]["minimum_to_start"])),
                    )
                    or part["share"] < Decimal("10")
                ),
            }
            for part, amount in zip(parts, amounts)
        ],
        "shares_total": str(sum((part["share"] for part in parts), ZERO)),
        "valid_total": sum((part["share"] for part in parts), ZERO) == HUNDRED,
        "allocated_total": str(sum(amounts, ZERO)),
    }


@router.post("/plan")
def save_plan(
    request: PlanInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Save one to seven chosen jars and advance the user to plan review."""
    profile = _profile_for_user(user, db)
    _require_choices_access(user, profile)
    try:
        plan = _save_plan(
            user,
            db,
            request.monthly_amount,
            [part.model_dump() for part in request.parts],
            request.tax_saving_80c,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _plan_response(plan)


@router.get("/plan")
def get_plan(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the signed-in user's saved choices, analysis and checklist."""
    return _plan_response(_get_plan(user, db))


@router.get("/plan/projector")
def get_plan_projector(
    years: int = Query(default=10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Project only the signed-in user's saved, positive-share plan parts."""
    plan = _get_plan(user, db)
    if plan is None:
        # A missing plan is an empty page state, not a server error.
        return {
            "exists": False,
            "parts": [],
            "totals": None,
            "series": [],
            "years": years,
            "label": "Expected, not guaranteed",
            "disclaimer": "Each growth number is an assumption, not a promise.",
        }

    catalog = _investment_catalog()
    saved_parts = []
    for saved_part in plan.parts or []:
        share = Decimal(str(saved_part.get("share", "0")))
        if share <= ZERO:
            # A zero share is not one of the user's chosen investments.
            continue
        idea_id = str(saved_part.get("idea_id", ""))
        idea = catalog.get(idea_id)
        if idea is None:
            raise HTTPException(
                status_code=409,
                detail="A saved plan idea is no longer available. Please edit your plan.",
            )
        saved_parts.append((saved_part, idea, share))
    if not saved_parts:
        raise HTTPException(
            status_code=409,
            detail="Your saved plan has no chosen investments. Please edit your plan.",
        )

    # Split the saved amount so the displayed rows add to every paise.
    try:
        amounts = split_monthly_amount(
            plan.monthly_amount,
            [share for _, _, share in saved_parts],
        )
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail="Your saved plan needs an update. Please edit your plan.",
        ) from error

    growth_parts = []
    rows = []
    for (saved_part, idea, share), monthly_amount in zip(saved_parts, amounts):
        # Keep each investment's own return range for every projection.
        growth_part = {
            "monthly_amount": monthly_amount,
            "expected_return_low": idea["expected_return_low"],
            "expected_return_mid": idea["expected_return_mid"],
            "expected_return_high": idea["expected_return_high"],
        }
        growth_parts.append(growth_part)
        part_growth = {
            str(period): calculate_plan_growth([growth_part], period)
            for period in (5, 10)
        }
        rows.append({
            "idea_id": str(saved_part["idea_id"]),
            "name": str(idea["name"]),
            "asset_class": str(idea["asset_class"]),
            "share": str(share),
            "monthly_amount": str(monthly_amount),
            "expected_return_low": str(idea["expected_return_low"]),
            "expected_return_mid": str(idea["expected_return_mid"]),
            "expected_return_high": str(idea["expected_return_high"]),
            "growth": {
                period: {
                    level: str(part_growth[period][level])
                    for level in ("low", "mid", "high")
                }
                for period in ("5", "10")
            },
        })

    # Add the rounded row values so the footer matches the visible table.
    totals = {
        "monthly": str(sum((Decimal(row["monthly_amount"]) for row in rows), ZERO)),
        "five_year_middle": str(sum(
            (Decimal(row["growth"]["5"]["mid"]) for row in rows),
            ZERO,
        )),
        "ten_year_middle": str(sum(
            (Decimal(row["growth"]["10"]["mid"]) for row in rows),
            ZERO,
        )),
    }
    series = []
    for period in range(1, years + 1):
        # Sum each saved part separately for this chart year.
        growth = calculate_plan_growth(growth_parts, period)
        series.append({
            "year": period,
            "low": str(growth["low"]),
            "mid": str(growth["mid"]),
            "high": str(growth["high"]),
            "invested": str(growth["invested"]),
        })

    return {
        "exists": True,
        "monthly_amount": str(plan.monthly_amount),
        "parts_count": len(rows),
        "parts": rows,
        "totals": totals,
        "years": years,
        "series": series,
        "label": "Expected, not guaranteed",
        "disclaimer": "Each growth number is an assumption, not a promise.",
    }


@router.get("/smart-amount/growth")
def get_smart_amount_growth(
    amount: Decimal = Query(ge=0, max_digits=16, decimal_places=2),
    years: int = Query(default=10, ge=1, le=30),
    expenses: Decimal | None = Query(default=None, ge=0, max_digits=16, decimal_places=2),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return one private amount projection or an expense-slider preview."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_data = {
        "income": profile.income if profile is not None else "0",
        "expenses": profile.expenses if profile is not None else "0",
        "savings": profile.savings if profile is not None else "0",
        "debts": profile.debts if profile is not None else [],
        "goals": profile.goals if profile is not None else [],
        "investor_type": profile.investor_type if profile is not None else "balanced",
    }
    plan = _get_plan(user, db)
    try:
        return calculate_amount_growth(
            amount,
            years,
            profile_data,
            plan.parts if plan is not None else None,
            get_market_snapshot(),
            expenses,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/smart-amount")
def save_smart_monthly_amount(
    request: SmartAmountSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Save a selected amount without changing any saved plan percentages."""
    profile = _profile_for_user(user, db)
    plan = _get_plan(user, db)
    amount = round_money(request.amount)
    if plan is not None:
        shares = [
            Decimal(str(part.get("share", "0")))
            for part in plan.parts or []
            if Decimal(str(part.get("share", "0"))) > ZERO
        ]
        if not shares or sum(shares, ZERO) != HUNDRED:
            raise HTTPException(
                status_code=409,
                detail="Your saved plan needs an update. Please edit your plan.",
            )
        try:
            amounts = split_monthly_amount(amount, shares)
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail="Your saved plan needs an update. Please edit your plan.",
            ) from error
        if sum(amounts, ZERO) != amount:
            raise HTTPException(
                status_code=409,
                detail="The plan parts did not add up. Please try again.",
            )
        plan.monthly_amount = str(amount)
        plan.analysis = None
        plan.is_stale = True

    profile.wanted_monthly_amount = str(amount)
    db.commit()
    if plan is not None:
        db.refresh(plan)
    record_progress_snapshot(user, db)
    return {
        "message": "Saved. Re-check your plan.",
        "monthly_amount": str(amount),
        "plan": _plan_response(plan),
    }


@router.post("/plan/analyze")
def analyze_saved_plan(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run the five plan checks, growth estimates and goal options again."""
    try:
        return _analyze_and_save(user, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/plan/apply-fix")
def apply_plan_fix(
    request: PlanFixInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Apply one real suggested fix and mark the saved analysis for review."""
    analysis = _analyze_and_save(user, db)
    fix = next(
        (item for item in analysis["top_fixes"] if item["id"] == request.fix_id),
        None,
    )
    if fix is None:
        raise HTTPException(status_code=404, detail="That plan fix is no longer available.")
    plan = _get_plan(user, db)
    if plan is None:
        raise HTTPException(status_code=404, detail="Save your plan before applying a fix.")
    try:
        updated = _save_plan(user, db, fix["monthly_amount"], fix["parts"])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"message": fix["label"], "plan": _plan_response(updated)}


@router.get("/plan/compare")
def compare_plans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compare the saved plan with an idea-by-idea ArthMitra suggestion."""
    profile, plan = _analysis_context(user, db)
    own = analyze_plan(_profile_data(profile), {
        "monthly_amount": plan.monthly_amount,
        "parts": plan.parts or [],
    })
    suggested_result = _suggestion(profile, plan.monthly_amount, plan.tax_saving_80c)
    suggested_parts = [
        {"idea_id": part["idea_id"], "share": str(part["share"])}
        for part in suggested_result["parts"]
    ]
    suggestion = {
        "monthly_amount": plan.monthly_amount,
        "parts": suggested_parts,
    }
    suggested = analyze_plan(_profile_data(profile), suggestion)
    own_ids = {part["idea_id"] for part in plan.parts or []}
    suggested_ids = {part["idea_id"] for part in suggested_parts}
    missing = suggested_ids - own_ids
    summary = (
        f"Your plan is close to ours. Only { _investment_catalog()[sorted(missing)[0]]['name'] } is missing."
        if missing
        else "Your plan uses the same ideas as ArthMitra's suggestion."
    )
    return {
        "your_plan": _plan_response(plan),
        "your_analysis": _json_safe(own),
        "suggested_plan": {
            **suggestion,
            "tax_saving_80c": bool(plan.tax_saving_80c),
        },
        "suggestion_details": _json_safe(suggested_result),
        "suggested_analysis": _json_safe(suggested),
        "summary": summary,
        "label": "Expected, not guaranteed",
    }


@router.post("/plan/confirm")
def confirm_plan(
    request: PlanConfirmInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Keep the saved plan or replace it with the suggestion, then finish setup."""
    profile, plan = _analysis_context(user, db)
    if request.choice == "suggested":
        _save_plan(
            user,
            db,
            plan.monthly_amount,
            [
                {"idea_id": part["idea_id"], "share": str(part["share"])}
                for part in _suggestion(
                    profile,
                    plan.monthly_amount,
                    plan.tax_saving_80c,
                )["parts"]
            ],
            plan.tax_saving_80c,
        )
    analysis = _analyze_and_save(user, db)
    user.onboarding_step = 4
    if user.plan_review_completed_at is None:
        user.plan_review_completed_at = datetime.now(timezone.utc)
    db.commit()
    record_progress_snapshot(user, db)
    return {
        "message": "Your plan is ready. You can learn, track tasks and edit it later.",
        "onboarding_step": 4,
        "analysis": analysis,
    }


@router.get("/plan/journey")
def plan_journey(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Show where, how, growth and calm investing rules for the saved plan."""
    profile, plan = _analysis_context(user, db)
    analysis = plan.analysis if plan.analysis and not plan.is_stale else _analyze_and_save(user, db)
    catalog = _investment_catalog()
    parts = []
    for part in plan.parts or []:
        idea = catalog[part["idea_id"]]
        parts.append({
            "idea_id": part["idea_id"],
            "name": idea["name"],
            "share": part["share"],
            "reason": idea.get("reason") or idea.get("school_explanation"),
            "steps": idea.get("how_to_start") or [
                "Check the current rules.", "Choose a safe place.", "Set an affordable monthly date."
            ],
        })
    return {
        "where": parts,
        "how": parts,
        "growth": analysis["growth"],
        "rules": [
            "Start early, but only with money you can leave for the needed time.",
            "Save or invest regularly when your budget allows.",
            "Spread money across parts instead of depending on one.",
            "Stay calm when prices fall; check your plan before making changes.",
        ],
        "do": ["Use a plan you understand.", "Check official rules and fees."],
        "dont": [
            "Do not chase tips.",
            "Do not invest money you need soon.",
            "Do not stop a plan only because markets fall.",
        ],
        "tasks": plan.tasks or [],
        "completed_tasks": sum(bool(task.get("completed")) for task in plan.tasks or []),
        "task_count": len(plan.tasks or []),
        "goal": analysis.get("goal"),
    }


@router.put("/plan/tasks/{task_id}")
def update_plan_task(
    task_id: str,
    request: PlanTaskInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Save a first-month task as done or not done."""
    plan = _get_plan(user, db)
    if plan is None:
        raise HTTPException(status_code=404, detail="Save a plan before checking off a task.")
    tasks = list(plan.tasks or [])
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="We could not find that plan task.")
    task["completed"] = request.completed
    plan.tasks = tasks
    db.commit()
    record_progress_snapshot(user, db)  # Keep the plan checklist change in report history.
    return {
        "task": task,
        "completed_tasks": sum(bool(item.get("completed")) for item in tasks),
        "task_count": len(tasks),
    }
