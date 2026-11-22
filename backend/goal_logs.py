"""Save owner-only goal investment logs and calculate their progress."""

import csv
import io
import math
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import extract
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.calculators import calculate_goal_investment_progress
from backend.database import get_db
from backend.investment_ideas import load_investment_ideas
from backend.models import (
    GoalLogHistory,
    GoalValueSnapshot,
    InvestmentLog,
    InvestmentPlan,
    Profile,
    User,
)
from backend.report import record_progress_snapshot
from backend.schemas import GoalInput, GoalLogInput, GoalValueInput


router = APIRouter()
ZERO = Decimal("0")
WRITE_LIMIT = 60
WRITE_WINDOW_SECONDS = 60
write_attempts: dict[int, deque[float]] = {}


def _utc_now() -> datetime:
    """Return one timezone-aware UTC timestamp for database changes."""
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """Treat old SQLite naive timestamps as UTC and normalize aware timestamps."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_user_time(value: datetime | None, timezone_name: str = "Asia/Kolkata") -> str | None:
    """Format a stored UTC time for a user's selected IANA timezone."""
    normalized = _as_utc(value)
    if normalized is None:
        return None
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Asia/Kolkata")
    local_time = normalized.astimezone(zone)
    return (
        f"{local_time.day:02d} {local_time.strftime('%b %Y')}, "
        f"{local_time.strftime('%I:%M %p').lstrip('0')}"
    )


def _iso_utc(value: datetime | None) -> str | None:
    """Return a timestamp in an unambiguous UTC ISO format."""
    normalized = _as_utc(value)
    return normalized.isoformat().replace("+00:00", "Z") if normalized else None


def _india_today() -> date:
    """Use India time for the current month and future-month checks."""
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _write_allowed(user_id: int) -> bool:
    """Limit each signed-in user to sixty log writes per minute."""
    now = time.monotonic()
    attempts = write_attempts.setdefault(user_id, deque())
    while attempts and now - attempts[0] > WRITE_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= WRITE_LIMIT:
        return False
    attempts.append(now)
    return True


def _check_write_limit(user: User) -> None:
    """Stop repeated changes before they can overload the log endpoints."""
    if not _write_allowed(user.id):
        raise HTTPException(
            status_code=429,
            detail="Too many updates. Please wait a minute and try again.",
        )


def ensure_goal_metadata(profile: Profile, user: User) -> list[dict]:
    """Give older JSON goals stable IDs and a safe backfill start date."""
    today = _india_today()
    fallback_date = (
        profile.updated_at.date()
        if profile.updated_at is not None
        else user.created_at.date()
    )
    goals = []
    seen_ids = set()
    for saved_goal in profile.goals or []:
        goal = dict(saved_goal)
        goal_id = str(goal.get("id") or "")
        if not goal_id or goal_id in seen_ids:
            goal_id = str(uuid4())
        seen_ids.add(goal_id)
        start_value = goal.get("start_date") or fallback_date.isoformat()
        try:
            start_date = date.fromisoformat(str(start_value)[:10])
        except ValueError:
            start_date = fallback_date
        if start_date > today:
            start_date = today
        goal["id"] = goal_id
        goal["start_date"] = start_date.isoformat()
        goals.append(goal)
    if goals != (profile.goals or []):
        profile.goals = goals
    return goals


def save_goal_records(
    profile: Profile,
    user: User,
    incoming_goals: list[GoalInput],
) -> list[dict]:
    """Keep goal IDs and start dates stable while saving the edited goal list."""
    existing = ensure_goal_metadata(profile, user)
    existing_by_id = {goal["id"]: goal for goal in existing}
    existing_by_name = {str(goal["name"]).casefold(): goal for goal in existing}
    saved_goals = []
    for incoming in incoming_goals:
        goal = incoming.model_dump(mode="json")
        previous = existing_by_id.get(goal.get("id")) if goal.get("id") else None
        if previous is None:
            previous = existing_by_name.get(str(goal["name"]).casefold())
        goal["id"] = goal.get("id") or (previous or {}).get("id") or str(uuid4())
        goal["start_date"] = (
            goal.get("start_date")
            or (previous or {}).get("start_date")
            or _india_today().isoformat()
        )
        saved_goals.append(goal)
    profile.goals = saved_goals
    return ensure_goal_metadata(profile, user)


def _goal_context(
    goal_id: str,
    user: User,
    db: Session,
) -> tuple[Profile, dict]:
    """Find a goal only inside the signed-in user's saved profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Goal not found.")
    goals = ensure_goal_metadata(profile, user)
    goal = next((item for item in goals if item["id"] == goal_id), None)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found.")
    db.commit()
    return profile, goal


def _plan_data(user: User, db: Session) -> tuple[Decimal, list[dict]]:
    """Read this user's plan and attach trusted middle rates to its parts."""
    plan = db.query(InvestmentPlan).filter(InvestmentPlan.user_id == user.id).first()
    if plan is None:
        return ZERO, []
    catalog = {str(item["id"]): item for item in load_investment_ideas()}
    parts = []
    for saved_part in plan.parts or []:
        idea_id = str(saved_part.get("idea_id", ""))
        idea = catalog.get(idea_id)
        if idea is None:
            continue
        parts.append({
            "idea_id": idea_id,
            "name": str(idea["name"]),
            "share": str(saved_part.get("share", "0")),
            "expected_return_mid": str(idea["expected_return_mid"]),
        })
    return Decimal(str(plan.monthly_amount)), parts


def _goal_logs(user: User, goal_id: str, db: Session) -> list[InvestmentLog]:
    """Fetch every active or deleted log with both ownership filters applied."""
    return (
        db.query(InvestmentLog)
        .filter(
            InvestmentLog.user_id == user.id,
            InvestmentLog.goal_id == goal_id,
        )
        .order_by(InvestmentLog.month.asc(), InvestmentLog.created_at.asc(), InvestmentLog.id.asc())
        .all()
    )


def _progress_data(
    goal_id: str,
    user: User,
    db: Session,
) -> dict:
    """Build the goal's progress response from this user's plan, logs and snapshot."""
    profile, goal = _goal_context(goal_id, user, db)
    planned_monthly, plan_parts = _plan_data(user, db)
    logs = _goal_logs(user, goal_id, db)
    snapshot = (
        db.query(GoalValueSnapshot)
        .filter(
            GoalValueSnapshot.user_id == user.id,
            GoalValueSnapshot.goal_id == goal_id,
        )
        .order_by(GoalValueSnapshot.taken_at.desc(), GoalValueSnapshot.id.desc())
        .first()
    )
    progress = calculate_goal_investment_progress(
        goal["amount"],
        goal["years"],
        goal["start_date"],
        planned_monthly,
        plan_parts,
        [
            {
                "amount": log.amount,
                "month": log.month,
                "part_id": log.part_id,
                "created_at": log.created_at,
                "updated_at": log.updated_at,
                "deleted_at": log.deleted_at,
            }
            for log in logs
        ],
        (
            {"value": snapshot.value, "taken_at": snapshot.taken_at}
            if snapshot is not None
            else None
        ),
        _india_today(),
    )
    return {
        **progress,
        "goal": {
            "id": goal["id"],
            "name": goal["name"],
            "amount": str(goal["amount"]),
            "years": goal["years"],
            "start_date": goal["start_date"],
        },
        "planned_monthly_amount": str(planned_monthly),
        "plan_parts": [
            {
                "idea_id": part["idea_id"],
                "name": part["name"],
                "share": part["share"],
                "expected_return_mid": part["expected_return_mid"],
            }
            for part in plan_parts
        ],
        "reminder_due": _india_today().day > 5 and not progress["current_month_logged"],
        "income": profile.income,
        "latest_value_snapshot": (
            {
                "value": str(snapshot.value),
                "taken_at": _iso_utc(snapshot.taken_at),
            }
            if snapshot is not None
            else None
        ),
    }


def get_goal_progress_for_user(goal_id: str, user: User, db: Session) -> dict:
    """Expose the same calculated goal facts to API and coach responses."""
    return _progress_data(goal_id, user, db)


def _latest_action(log: InvestmentLog, user: User, db: Session) -> str:
    """Read the newest owner-filtered audit action for one saved log."""
    history = (
        db.query(GoalLogHistory)
        .filter(
            GoalLogHistory.user_id == user.id,
            GoalLogHistory.log_id == log.id,
        )
        .order_by(GoalLogHistory.changed_at.desc(), GoalLogHistory.id.desc())
        .first()
    )
    return history.action if history is not None else "Added"


def _log_response(log: InvestmentLog, user: User, db: Session) -> dict:
    """Return one log, its audit rows and a simple current status."""
    history = (
        db.query(GoalLogHistory)
        .filter(
            GoalLogHistory.user_id == user.id,
            GoalLogHistory.log_id == log.id,
        )
        .order_by(GoalLogHistory.changed_at.desc(), GoalLogHistory.id.desc())
        .all()
    )
    action = history[0].action if history else "Added"
    if log.deleted_at is not None:
        status_text = "Deleted"
    elif action == "Edited" or any(row.action == "Edited" for row in history):
        status_text = "Edited"
    else:
        status_text = "Added"
    return {
        "id": log.id,
        "goal_id": log.goal_id,
        "month": log.month.strftime("%Y-%m"),
        "amount": str(log.amount),
        "part_id": log.part_id,
        "note": log.note,
        "created_at": _iso_utc(log.created_at),
        "updated_at": _iso_utc(log.updated_at),
        "deleted_at": _iso_utc(log.deleted_at),
        "status": status_text,
        "undo_until": (
            _iso_utc(_as_utc(log.deleted_at) + timedelta(seconds=10))
            if log.deleted_at is not None
            else None
        ),
        "history": [
            {
                "action": row.action,
                "old_amount": str(row.old_amount) if row.old_amount is not None else None,
                "new_amount": str(row.new_amount) if row.new_amount is not None else None,
                "old_part_id": row.old_part_id,
                "new_part_id": row.new_part_id,
                "old_note": row.old_note,
                "new_note": row.new_note,
                "changed_by": row.user_id,
                "changed_at": _iso_utc(row.changed_at),
            }
            for row in history
        ],
    }


def _audit(
    db: Session,
    user: User,
    log: InvestmentLog,
    action: str,
    old_amount: Decimal | None,
    new_amount: Decimal | None,
    old_part_id: str | None,
    new_part_id: str | None,
    old_note: str | None,
    new_note: str | None,
) -> None:
    """Save an owner-scoped before-and-after audit row for a log change."""
    db.add(GoalLogHistory(
        log_id=log.id,
        user_id=user.id,
        action=action,
        old_amount=old_amount,
        new_amount=new_amount,
        old_part_id=old_part_id,
        new_part_id=new_part_id,
        old_note=old_note,
        new_note=new_note,
        changed_at=_utc_now(),
    ))


def _month_start(value: date) -> date:
    """Normalize any valid day to the first day of its selected month."""
    return value.replace(day=1)


def _validate_log_month(month: date, goal: dict) -> date:
    """Reject future months and dates before the saved goal start month."""
    selected = _month_start(month)
    current = _month_start(_india_today())
    start = date.fromisoformat(goal["start_date"])
    if selected > current:
        raise HTTPException(status_code=422, detail="Choose this month or an earlier month.")
    if selected < _month_start(start):
        raise HTTPException(
            status_code=422,
            detail="Choose a month on or after this goal's start date.",
        )
    return selected


def _validate_part_id(part_id: str | None, parts: list[dict]) -> None:
    """Allow an optional idea only when it belongs to this user's saved plan."""
    if part_id and part_id not in {str(part["idea_id"]) for part in parts}:
        raise HTTPException(
            status_code=422,
            detail="Choose an idea from your saved plan, or leave this field blank.",
        )


def _duplicate_result(
    logs: list[InvestmentLog],
    user: User,
    db: Session,
) -> dict:
    """Show the user's existing monthly rows so they can add or edit one."""
    return {
        "needs_choice": True,
        "message": "You already logged this month. Add to it or edit it?",
        "existing_logs": [_log_response(log, user, db) for log in logs],
    }


def _log_warnings(amount: Decimal, planned: Decimal, income: str | None) -> list[str]:
    """Warn without blocking an amount above the plan or monthly income."""
    warnings = []
    if planned > ZERO and amount > planned * Decimal("3"):
        warnings.append("This is more than 3 times your planned monthly amount.")
    if income is not None and amount > Decimal(str(income)):
        warnings.append("This amount is more than your monthly income.")
    return warnings


def _find_owned_log(log_id: int, user: User, db: Session) -> InvestmentLog:
    """Find one log by both its ID and the signed-in owner's ID."""
    log = (
        db.query(InvestmentLog)
        .filter(InvestmentLog.id == log_id, InvestmentLog.user_id == user.id)
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="Investment update not found.")
    return log


@router.get("/goals")
def list_goals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return this user's goals with stable IDs and their saved start dates."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        return {"goals": []}
    goals = ensure_goal_metadata(profile, user)
    db.commit()
    return {"goals": goals}


@router.get("/goals/{goal_id}/progress")
def goal_progress(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return backend-only invested value, plan comparison, and consistency facts."""
    try:
        return _progress_data(goal_id, user, db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/goals/{goal_id}/logs")
def create_goal_log(
    goal_id: str,
    request: GoalLogInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Save a monthly investment or skipped-month record for an owned goal."""
    _check_write_limit(user)
    profile, goal = _goal_context(goal_id, user, db)
    month = _validate_log_month(request.month, goal)
    planned, parts = _plan_data(user, db)
    _validate_part_id(request.part_id, parts)
    existing = (
        db.query(InvestmentLog)
        .filter(
            InvestmentLog.user_id == user.id,
            InvestmentLog.goal_id == goal_id,
            InvestmentLog.month == month,
            InvestmentLog.deleted_at.is_(None),
        )
        .order_by(InvestmentLog.updated_at.desc(), InvestmentLog.id.desc())
        .all()
    )
    if existing and not request.add_to_month:
        return _duplicate_result(existing, user, db)
    now = _utc_now()
    log = InvestmentLog(
        user_id=user.id,
        goal_id=goal_id,
        month=month,
        amount=request.amount,
        part_id=request.part_id,
        note=request.note,
        created_at=now,
        updated_at=now,
    )
    db.add(log)
    db.flush()
    _audit(db, user, log, "Added", None, request.amount, None, request.part_id, None, request.note)
    db.commit()
    db.refresh(log)
    record_progress_snapshot(user, db)  # Keep the new investment in the report timeline.
    return {
        "log": _log_response(log, user, db),
        "warnings": _log_warnings(request.amount, planned, profile.income),
        "progress": _progress_data(goal_id, user, db),
        "message": "Investment update saved.",
    }


@router.get("/goals/{goal_id}/logs")
def list_goal_logs(
    goal_id: str,
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=1970, le=9999),
    page: int = Query(default=1, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return ten newest history rows at a time with optional month and year filters."""
    _goal_context(goal_id, user, db)
    query = db.query(InvestmentLog).filter(
        InvestmentLog.user_id == user.id,
        InvestmentLog.goal_id == goal_id,
    )
    if month is not None:
        query = query.filter(extract("month", InvestmentLog.month) == month)
    if year is not None:
        query = query.filter(
            InvestmentLog.month >= date(year, 1, 1),
            InvestmentLog.month < date(year + 1, 1, 1),
        )
    total = query.count()
    logs = (
        query.order_by(InvestmentLog.updated_at.desc(), InvestmentLog.id.desc())
        .offset((page - 1) * 10)
        .limit(10)
        .all()
    )
    return {
        "logs": [_log_response(log, user, db) for log in logs],
        "page": page,
        "page_size": 10,
        "total": total,
        "pages": math.ceil(total / 10) if total else 0,
    }


@router.put("/logs/{log_id}")
def update_goal_log(
    log_id: int,
    request: GoalLogInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Edit an owned log and keep its former values in the audit table."""
    _check_write_limit(user)
    log = _find_owned_log(log_id, user, db)
    if log.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Investment update not found.")
    profile, goal = _goal_context(log.goal_id, user, db)
    month = _validate_log_month(request.month, goal)
    planned, parts = _plan_data(user, db)
    _validate_part_id(request.part_id, parts)
    duplicates = (
        db.query(InvestmentLog)
        .filter(
            InvestmentLog.user_id == user.id,
            InvestmentLog.goal_id == log.goal_id,
            InvestmentLog.month == month,
            InvestmentLog.deleted_at.is_(None),
            InvestmentLog.id != log.id,
        )
        .all()
    )
    if duplicates and not request.add_to_month:
        return _duplicate_result(duplicates, user, db)
    old_amount, old_part, old_note = log.amount, log.part_id, log.note
    log.month = month
    log.amount = request.amount
    log.part_id = request.part_id
    log.note = request.note
    log.updated_at = _utc_now()
    _audit(
        db, user, log, "Edited", old_amount, request.amount,
        old_part, request.part_id, old_note, request.note,
    )
    db.commit()
    db.refresh(log)
    record_progress_snapshot(user, db)  # Save the edited investment in report history.
    return {
        "log": _log_response(log, user, db),
        "warnings": _log_warnings(request.amount, planned, profile.income),
        "progress": _progress_data(log.goal_id, user, db),
        "message": "Investment update changed.",
    }


@router.delete("/logs/{log_id}")
def delete_goal_log(
    log_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Soft-delete one owned log and allow undo for ten seconds."""
    _check_write_limit(user)
    log = _find_owned_log(log_id, user, db)
    if log.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Investment update not found.")
    old_amount, old_part, old_note = log.amount, log.part_id, log.note
    now = _utc_now()
    log.deleted_at = now
    log.updated_at = now
    _audit(db, user, log, "Deleted", old_amount, None, old_part, None, old_note, None)
    db.commit()
    db.refresh(log)
    record_progress_snapshot(user, db)  # Record the removal but keep its soft-delete history.
    return {
        "log": _log_response(log, user, db),
        "undo_until": _iso_utc(now + timedelta(seconds=10)),
        "message": "Update deleted. You can undo it for 10 seconds.",
    }


@router.post("/logs/{log_id}/undo")
def undo_goal_log(
    log_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Restore a soft-deleted log only during its ten-second undo window."""
    _check_write_limit(user)
    log = _find_owned_log(log_id, user, db)
    deleted_at = _as_utc(log.deleted_at)
    if deleted_at is None:
        raise HTTPException(status_code=404, detail="Deleted update not found.")
    if _utc_now() - deleted_at > timedelta(seconds=10):
        raise HTTPException(status_code=410, detail="The 10-second undo time has passed.")
    old_amount, old_part, old_note = log.amount, log.part_id, log.note
    log.deleted_at = None
    log.updated_at = _utc_now()
    _audit(
        db, user, log, "Restored", old_amount, old_amount,
        old_part, old_part, old_note, old_note,
    )
    db.commit()
    db.refresh(log)
    record_progress_snapshot(user, db)  # Record the restored investment in report history.
    return {
        "log": _log_response(log, user, db),
        "progress": _progress_data(log.goal_id, user, db),
        "message": "Update restored.",
    }


@router.post("/goals/{goal_id}/value")
def save_goal_value(
    goal_id: str,
    request: GoalValueInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Save a dated value from the user's account or investment statement."""
    _check_write_limit(user)
    _goal_context(goal_id, user, db)
    snapshot = GoalValueSnapshot(
        user_id=user.id,
        goal_id=goal_id,
        value=request.value,
        taken_at=_utc_now(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    record_progress_snapshot(user, db)  # Save the updated real value in the report timeline.
    return {
        "snapshot": {
            "value": str(snapshot.value),
            "taken_at": _iso_utc(snapshot.taken_at),
        },
        "progress": _progress_data(goal_id, user, db),
        "message": "Today's value was saved.",
    }


@router.get("/goals/{goal_id}/logs/export")
def export_goal_logs(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download all owner-filtered goal history rows as a CSV file."""
    _goal_context(goal_id, user, db)
    logs = _goal_logs(user, goal_id, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date and time (UTC)", "Month", "Amount", "Part", "Note", "Status"])
    for log in sorted(logs, key=lambda row: (_as_utc(row.updated_at), row.id), reverse=True):
        response = _log_response(log, user, db)
        writer.writerow([
            response["updated_at"],
            response["month"],
            response["amount"],
            response["part_id"] or "",
            response["note"] or "",
            response["status"],
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="goal-{goal_id}-logs.csv"'},
    )
