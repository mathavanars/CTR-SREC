"""Validate API input and describe safe response shapes with Pydantic."""

import re
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """A new user's email and password."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Accept a plain email shape and return it in lowercase."""
        email = email.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Please enter a valid email address.")
        return email


class LoginRequest(BaseModel):
    """An email and password used to log in."""

    email: str = Field(min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, email: str) -> str:
        """Ignore letter case and spaces around the login email."""
        return email.strip().lower()


class AuthResponse(BaseModel):
    """A logged-in response with one JWT token."""

    access_token: str
    token_type: str = "bearer"


class DebtInput(BaseModel):
    """One debt amount, interest rate and monthly EMI."""

    name: str = "Debt"  # Keep a friendly name when a full profile omits one.
    amount: Decimal = Decimal("0")  # Let validators return clear amount errors.
    interest_rate: Decimal = Decimal("0")  # Use a zero rate when none is supplied.
    emi: Decimal = Decimal("0")  # Use a zero payment when none is supplied.

    @field_validator("name")  # Check that every debt name is readable.
    @classmethod  # Let Pydantic call this check on debt inputs.
    def validate_name(cls, name: str) -> str:  # Return a clean debt name.
        cleaned = name.strip()  # Remove spaces around the name.
        if not cleaned:  # Stop an empty debt name.
            raise ValueError("Debt name cannot be empty.")  # Explain how to fix the name.
        if len(cleaned) > 100:  # Keep the name short enough for the form.
            raise ValueError("Debt name must be 100 characters or fewer.")  # Explain the name limit.
        return cleaned  # Save the trimmed debt name.

    @field_validator("amount")  # Check that the debt balance is not negative.
    @classmethod  # Let Pydantic call this amount check.
    def validate_amount(cls, amount: Decimal) -> Decimal:  # Return the checked balance.
        if amount < 0:  # Reject negative debt balances.
            raise ValueError("Debt amount cannot be negative.")  # Explain the balance rule.
        return amount  # Keep the valid debt balance.

    @field_validator("interest_rate")  # Check the supported debt-rate range.
    @classmethod  # Let Pydantic call this rate check.
    def validate_interest_rate(cls, rate: Decimal) -> Decimal:  # Return the checked rate.
        if rate < 0 or rate > 60:  # Keep rates between zero and sixty percent.
            raise ValueError("Interest rate must be between 0 and 60%.")  # Explain the rate rule.
        return rate  # Keep the valid annual rate.

    @field_validator("emi")  # Check that the monthly payment is not negative.
    @classmethod  # Let Pydantic call this payment check.
    def validate_emi(cls, emi: Decimal) -> Decimal:  # Return the checked payment.
        if emi < 0:  # Reject a negative monthly payment.
            raise ValueError("Monthly EMI cannot be negative.")  # Explain the payment rule.
        return emi  # Keep the valid monthly payment.


class GoalInput(BaseModel):
    """One named saving goal with amount and years."""

    id: str | None = None  # Keep a stable identifier when this saved goal is edited.
    name: str  # Require each goal to have a name.
    amount: Decimal  # Let the validator explain invalid goal amounts.
    years: int  # Let the validator explain invalid goal timelines.
    start_date: date | None = None  # Keep the first goal date for backfilled monthly logs.

    @field_validator("id")  # Check that a saved goal identifier has a stable UUID shape.
    @classmethod  # Let Pydantic call this identifier check.
    def validate_id(cls, goal_id: str | None) -> str | None:  # Return a normalized UUID string.
        if goal_id is None:  # Allow new goals to receive an ID when they are saved.
            return None  # Leave creation to the authenticated API.
        try:  # Parse the supplied identifier as a UUID.
            return str(UUID(goal_id))  # Keep one canonical string form.
        except (ValueError, TypeError, AttributeError):  # Reject identifiers with another shape.
            raise ValueError("Goal ID is not valid. Please refresh the page and try again.")  # Explain how to fix it.

    @field_validator("name")  # Check that every goal name is readable.
    @classmethod  # Let Pydantic call this name check.
    def validate_name(cls, name: str) -> str:  # Return a clean goal name.
        cleaned = name.strip()  # Remove spaces around the name.
        if not cleaned:  # Stop an empty goal name.
            raise ValueError("Goal name cannot be empty.")  # Explain how to fix the name.
        if len(cleaned) > 100:  # Keep the name short enough for the form.
            raise ValueError("Goal name must be 100 characters or fewer.")  # Explain the name limit.
        return cleaned  # Save the trimmed goal name.

    @field_validator("amount")  # Check that the goal amount is positive.
    @classmethod  # Let Pydantic call this amount check.
    def validate_amount(cls, amount: Decimal) -> Decimal:  # Return the checked amount.
        if amount <= 0:  # Reject zero and negative goal amounts.
            raise ValueError("Goal amount must be greater than zero.")  # Explain the amount rule.
        return amount  # Keep the valid goal amount.

    @field_validator("years")  # Check that the goal timeline is supported.
    @classmethod  # Let Pydantic call this timeline check.
    def validate_years(cls, years: int) -> int:  # Return the checked timeline.
        if years < 1 or years > 50:  # Keep the goal between one and fifty years.
            raise ValueError("Years to reach a goal must be from 1 to 50.")  # Explain the timeline rule.
        return years  # Keep the valid number of years.


class GoalLogInput(BaseModel):
    """One monthly amount logged for a goal and an optional saved plan part."""

    month: date  # Keep a calendar month separate from the UTC creation time.
    amount: Decimal  # Let the validator return a clear money error.
    part_id: str | None = None  # Match an optional idea to the user's saved plan.
    note: str | None = None  # Keep a short optional note with the entry.
    add_to_month: bool = False  # Confirm a second entry after the duplicate warning.

    @field_validator("amount")  # Check that a logged investment cannot be negative.
    @classmethod  # Let Pydantic call this amount check.
    def validate_log_amount(cls, amount: Decimal) -> Decimal:  # Return the checked amount.
        if amount < 0:  # Reject negative investments.
            raise ValueError("Amount invested cannot be negative.")  # Explain the amount rule.
        return amount  # Keep the valid exact amount.

    @field_validator("part_id")  # Clean an optional saved idea identifier.
    @classmethod  # Let Pydantic call this part check.
    def clean_part_id(cls, part_id: str | None) -> str | None:  # Return an empty value as no selection.
        cleaned = part_id.strip() if part_id is not None else ""  # Remove spaces around the ID.
        return cleaned or None  # Store no part when the dropdown is blank.

    @field_validator("note")  # Enforce the requested short note length.
    @classmethod  # Let Pydantic call this note check.
    def clean_note(cls, note: str | None) -> str | None:  # Return a trimmed note or no note.
        cleaned = note.strip() if note is not None else ""  # Remove extra spaces around the note.
        if len(cleaned) > 200:  # Stop notes that are too long.
            raise ValueError("Note must be 200 characters or fewer.")  # Explain the note limit.
        return cleaned or None  # Keep empty notes out of the database.


class GoalValueInput(BaseModel):
    """One dated real-world value entered for a goal."""

    value: Decimal  # Keep the entered total as Decimal.

    @field_validator("value")  # Check that a current value cannot be negative.
    @classmethod  # Let Pydantic call this snapshot check.
    def validate_value(cls, value: Decimal) -> Decimal:  # Return the checked snapshot value.
        if value < 0:  # Reject negative values.
            raise ValueError("Investment value cannot be negative.")  # Explain the value rule.
        return value  # Keep the valid exact value.


class ProfileInput(BaseModel):
    """Monthly money details and planning lists supplied by the user."""

    income: Decimal = Field(gt=0)
    expenses: Decimal = Field(ge=0)
    savings: Decimal = Field(ge=0)
    debts: list[DebtInput] = Field(default_factory=list)
    goals: list[GoalInput] = Field(default_factory=list)
    income_stability: Literal["steady", "sometimes_changes", "irregular"] | None = None  # Keep optional profile edits backward compatible.
    wanted_monthly_amount: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)  # Save the user's preferred SIP.


class InvestmentCapacityPatch(BaseModel):  # Validate the amount and income stability without replacing other profile data.
    income_stability: Literal["steady", "sometimes_changes", "irregular"] | None = None  # Accept one of the three clear choices.
    wanted_monthly_amount: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)  # Keep zero as a valid chosen amount.

    @field_validator("income_stability")  # Give a friendly error for an unknown stability choice.
    @classmethod  # Let Pydantic call the stability check.
    def validate_income_stability(cls, value: str | None) -> str | None:  # Keep valid stability text unchanged.
        if value is not None and value not in {"steady", "sometimes_changes", "irregular"}:  # Check the supported choices.
            raise ValueError("Choose steady, sometimes changing or irregular income.")  # Explain the supported choices.
        return value  # Return the checked choice.


class DebtPatchItem(DebtInput):  # Require a name when editing one debt.
    name: str  # Do not silently supply a name in a section-only update.


class ProfileGoalsPatch(BaseModel):  # Describe a goals-only profile update.
    goals: list[GoalInput]  # Replace only the saved goals list.


class ProfileDebtsPatch(BaseModel):  # Describe a debts-only profile update.
    debts: list[DebtPatchItem]  # Replace only the saved debts list.


class ProfileResponse(BaseModel):
    """The profile shown after it is saved or requested."""

    income: str | None = None
    expenses: str | None = None
    savings: str | None = None
    debts: list[dict]
    goals: list[dict]
    email: str | None = None
    investor_type: str | None = None
    updated_at: str | None = None
    income_stability: str = "steady"  # Let older profiles use the safest default.
    wanted_monthly_amount: str | None = None  # Return the saved amount as exact text.


class ChangePasswordRequest(BaseModel):
    """The current password and the new password entered twice."""

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def confirm_new_password(cls, confirm_password: str, info) -> str:
        """Make sure both new password boxes match."""
        new_password = info.data.get("new_password")
        if new_password and confirm_password != new_password:
            raise ValueError("The new passwords do not match.")
        return confirm_password


class AllocationPlanInput(BaseModel):
    """One monthly amount used to build the signed-in user's plan."""

    monthly_amount: Decimal = Field(ge=0, max_digits=16, decimal_places=2)


class PlanPartInput(BaseModel):
    """One selected idea and its percentage of a monthly plan."""

    idea_id: str = Field(min_length=1, max_length=50)
    share: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=2)


class PlanInput(BaseModel):
    """A monthly amount split across one to seven chosen ideas."""

    monthly_amount: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    parts: list[PlanPartInput] = Field(min_length=1, max_length=7)
    tax_saving_80c: bool = False


class PlanFixInput(BaseModel):
    """The suggested fix the user wants to apply to their saved plan."""

    fix_id: str = Field(min_length=1, max_length=50)


class PlanConfirmInput(BaseModel):
    """The user's choice between their own plan and the suggested plan."""

    choice: Literal["mine", "suggested"]


class PlanTaskInput(BaseModel):
    """Whether a first-month checklist task is complete."""

    completed: bool


class ProjectionInput(BaseModel):
    """The amount, assumed yearly rate and years for a growth example."""

    monthly_amount: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    annual_rate: Decimal = Field(ge=0, le=40)
    years: int = Field(ge=1, le=50)


class ChatRequest(BaseModel):
    """A coach question and, optionally, a monthly amount to split."""

    question: str = Field(min_length=1, max_length=1000)
    monthly_amount: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)


class SmartAmountSaveRequest(BaseModel):
    """A selected monthly amount and the card choice that supplied it."""

    choice: Literal["comfortable", "recommended", "stretch", "want", "custom"]
    amount: Decimal = Field(ge=0, max_digits=16, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def validate_amount_step(cls, amount: Decimal, info) -> Decimal:
        """Require whole hundreds except for the user's already-typed amount."""
        if info.data.get("choice") != "want" and amount % Decimal("100") != 0:
            raise ValueError("Choose an amount in steps of Rs 100.")
        return amount


class AllocationItemResponse(BaseModel):
    """One idea's share and its estimated growth examples."""

    idea_id: str
    name: str
    asset_class: str
    monthly_amount: str
    expected_return_low: Decimal
    expected_return_mid: Decimal
    expected_return_high: Decimal
    growth: dict[str, dict[str, str]]
    label: str


class AllocationTotalsResponse(BaseModel):  # Describe the three exact totals shown under the table.
    """Keep the plan totals as precise decimal strings."""  # Explain why the totals remain strings.

    monthly: str  # Return the sum of all monthly amounts.
    five_year_middle: str  # Return the sum of all five-year middle estimates.
    ten_year_middle: str  # Return the sum of all ten-year middle estimates.


class AllocationPlanResponse(BaseModel):
    """A full split or a friendly explanation why a plan is not ready."""

    ready: bool
    monthly_amount: str
    investor_type: str
    items: list[AllocationItemResponse] = Field(default_factory=list)
    totals: AllocationTotalsResponse | None = None  # Include exact backend totals when a plan is ready.
    total: str | None = None
    summary: str | None = None
    label: str | None = None
    fix_plan: list[str] = Field(default_factory=list)


class RiskQuizInput(BaseModel):
    """Seven answers that explain how comfortable the user is with risk."""

    answers: list[int] = Field(min_length=7, max_length=7)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: list[int]) -> list[int]:
        """Keep every answer between 1 and 5 so the score stays clear."""
        if any(answer < 1 or answer > 5 for answer in answers):
            raise ValueError("Each risk answer must be between 1 and 5.")
        return answers


class RiskQuizResponse(BaseModel):
    """The investor type and plain-English reason for the quiz score."""

    investor_type: str
    score: int
    explanation: str


class ReadinessResponse(BaseModel):
    """A list of basics that are ready or need attention first."""

    ready: bool
    emergency_fund_months: str
    has_high_interest_debt: bool
    savings_rate: str
    checks: list[dict]
    fix_plan: list[str]


class AssetMixResponse(BaseModel):
    """How a suggested portfolio is split across simple categories."""

    investor_type: str
    equity: int
    debt: int
    gold: int
    fd_cash: int
    expected_return_range: str
    reasons: dict[str, str]
