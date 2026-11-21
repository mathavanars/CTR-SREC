"""
schemas.py
Pydantic schemas for requests and responses.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: Optional[str] = "First-time Investor"

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class LoanItem(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: str # home, personal, education, vehicle, credit_card, other
    outstanding_amount: float = Field(ge=0.0)
    interest_rate: float = Field(ge=0.0, le=100.0)
    emi: float = Field(ge=0.0)
    remaining_tenure: int = Field(ge=0) # in months

class InvestmentItem(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: str # fd, mutual_fund, stocks, gold, ppf_nps, epf, real_estate, other
    current_value: float = Field(ge=0.0)
    monthly_contribution: float = Field(default=0.0, ge=0.0)

class GoalItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = "General" # emergency, education, house, retirement, vehicle, travel, other
    target_amount: float = Field(ge=1000.0)
    current_saved: float = Field(default=0.0, ge=0.0)
    target_date: str # YYYY-MM
    priority: str = "Medium" # High, Medium, Low

class UserProfileUpdate(BaseModel):
    age: int = Field(default=28, ge=18, le=90)
    retirement_age: int = Field(default=60, ge=30, le=80)
    risk_appetite: str = "Medium" # Low, Medium, High
    dependents: int = Field(default=0, ge=0, le=20)
    monthly_income: float = Field(default=0.0, ge=0.0)
    savings: float = Field(default=0.0, ge=0.0) # Cash and bank balance
    fixed_expenses: Dict[str, float] = {}
    variable_expenses: Dict[str, float] = {}
    investments: List[InvestmentItem] = []
    loans: List[LoanItem] = []
    goals: List[GoalItem] = []

class UserProfileResponse(BaseModel):
    age: int
    retirement_age: int
    risk_appetite: str
    dependents: int
    monthly_income: float
    savings: float
    fixed_expenses: Dict[str, float]
    variable_expenses: Dict[str, float]
    investments: List[Dict[str, Any]]
    loans: List[Dict[str, Any]]
    goals: List[Dict[str, Any]]

class WhatIfRequest(BaseModel):
    extra_monthly_savings: float = 0.0
    return_adjustment: float = 0.0
    inflation_adjustment: float = 0.0
    retirement_age_override: Optional[int] = None
    loan_prepayment_monthly: float = 0.0

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "en" # "en", "hi", "ta"

class ChatResponse(BaseModel):
    reply: str
    language: str
    context_used: List[str] = []
