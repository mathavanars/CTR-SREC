"""
main.py
FastAPI application for ArthMitra AI Financial Coach.
"""
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json

from database import engine, Base, get_db
import models
import schemas
from auth import hash_password, verify_password, create_access_token, get_current_user
from config import settings
from personas import PERSONAS
from finance_engine import (
    calculate_cashflow,
    calculate_emergency_fund,
    calculate_financial_health_score,
    generate_monthly_action_plan,
    simulate_whatif
)
from agents.financial_agent import FinancialAgent
from agents.debt_agent import DebtAgent
from agents.goal_agent import GoalAgent
from agents.investment_agent import InvestmentAgent
from agents.coach_agent import CoachAgent
from agents.report_agent import report_agent

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ArthMitra: Transparent, AI-grounded personal finance coach for Indian first-time investors.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate Agents
financial_agent = FinancialAgent()
debt_agent = DebtAgent()
goal_agent = GoalAgent()
investment_agent = InvestmentAgent()
coach_agent = CoachAgent()

def run_full_analysis(profile_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to run the full financial analysis pipeline on any profile dictionary."""
    fin_res = financial_agent.analyze(profile_dict)
    cashflow = fin_res["cashflow"]
    emergency = fin_res["emergency"]
    
    debt = debt_agent.analyze(profile_dict, cashflow["savings_capacity"])
    goals = goal_agent.analyze(profile_dict, cashflow["savings_capacity"])
    
    invest_res = investment_agent.analyze(
        profile=profile_dict,
        monthly_savings_capacity=cashflow["savings_capacity"],
        has_emergency_gap=(emergency["gap"] > 0),
        monthly_expenses=cashflow["total_expenses"]
    )
    allocation = invest_res["allocation"]
    retirement = invest_res["retirement"]
    
    # Financial health score
    fixed_exp = profile_dict.get("fixed_expenses", {})
    has_insur = profile_dict.get("dependents", 0) == 0 or any("insur" in str(k).lower() for k in fixed_exp.keys())
    
    health_score = calculate_financial_health_score(
        savings_rate=cashflow["savings_rate"],
        emergency_months_covered=emergency["months_covered"],
        dti_ratio=debt.get("dti_ratio", 0.0),
        investments_count=len(profile_dict.get("investments", [])),
        goals_feasible_ratio=goals.get("goals_on_track_ratio", 100.0),
        has_insurance_or_dependents_covered=has_insur
    )
    
    action_plan = generate_monthly_action_plan(cashflow, emergency, debt, goals, retirement)
    
    return {
        "health_score": health_score,
        "cashflow": cashflow,
        "emergency": emergency,
        "debt": debt,
        "goals": goals,
        "allocation": allocation,
        "retirement": retirement,
        "action_plan": action_plan,
        "disclaimer": "This is educational guidance, not registered investment advice. Please consult a SEBI-registered advisor before investing."
    }

# ----------------- Auth Endpoints ----------------- #

@app.post("/api/v1/auth/register", response_model=schemas.Token)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
        
    hashed = hash_password(user_in.password)
    user = models.User(email=user_in.email, hashed_password=hashed, full_name=user_in.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create default empty profile with default persona (Salaried with loan)
    default_p = PERSONAS["salaried_with_loan"]["profile"]
    profile = models.UserProfile(
        user_id=user.id,
        age=default_p["age"],
        retirement_age=default_p["retirement_age"],
        risk_appetite=default_p["risk_appetite"],
        dependents=default_p["dependents"],
        monthly_income=default_p["monthly_income"],
        savings=default_p["savings"],
        fixed_expenses_json=json.dumps(default_p["fixed_expenses"]),
        variable_expenses_json=json.dumps(default_p["variable_expenses"]),
        investments_json=json.dumps(default_p["investments"]),
        loans_json=json.dumps(default_p["loans"]),
        goals_json=json.dumps(default_p["goals"])
    )
    db.add(profile)
    db.commit()
    
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name}
    }

@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
        
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name}
    }

# ----------------- Profile Endpoints ----------------- #

@app.get("/api/v1/profile")
def get_profile(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile.to_profile_dict()

@app.put("/api/v1/profile")
def update_profile(
    profile_in: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.UserProfile(user_id=current_user.id)
        db.add(profile)
        
    profile.age = profile_in.age
    profile.retirement_age = profile_in.retirement_age
    profile.risk_appetite = profile_in.risk_appetite
    profile.dependents = profile_in.dependents
    profile.monthly_income = profile_in.monthly_income
    profile.savings = profile_in.savings
    profile.fixed_expenses_json = json.dumps(profile_in.fixed_expenses)
    profile.variable_expenses_json = json.dumps(profile_in.variable_expenses)
    profile.investments_json = json.dumps([i.model_dump() for i in profile_in.investments])
    profile.loans_json = json.dumps([l.model_dump() for l in profile_in.loans])
    profile.goals_json = json.dumps([g.model_dump() for g in profile_in.goals])
    
    db.commit()
    db.refresh(profile)
    return profile.to_profile_dict()

# ----------------- Personas Endpoints ----------------- #

@app.get("/api/v1/personas")
def list_personas():
    return [
        {"id": k, "name": v["name"], "tagline": v["tagline"], "description": v["description"]}
        for k, v in PERSONAS.items()
    ]

@app.post("/api/v1/personas/{persona_id}/load")
def load_persona(
    persona_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found.")
        
    p_data = PERSONAS[persona_id]["profile"]
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.UserProfile(user_id=current_user.id)
        db.add(profile)
        
    profile.age = p_data["age"]
    profile.retirement_age = p_data["retirement_age"]
    profile.risk_appetite = p_data["risk_appetite"]
    profile.dependents = p_data["dependents"]
    profile.monthly_income = p_data["monthly_income"]
    profile.savings = p_data["savings"]
    profile.fixed_expenses_json = json.dumps(p_data["fixed_expenses"])
    profile.variable_expenses_json = json.dumps(p_data["variable_expenses"])
    profile.investments_json = json.dumps(p_data["investments"])
    profile.loans_json = json.dumps(p_data["loans"])
    profile.goals_json = json.dumps(p_data["goals"])
    
    db.commit()
    db.refresh(profile)
    return {"message": f"Successfully switched to persona: {PERSONAS[persona_id]['name']}", "profile": profile.to_profile_dict()}

# ----------------- Analysis Endpoints ----------------- #

@app.get("/api/v1/analysis/full")
def get_full_analysis(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile_dict = profile.to_profile_dict()
    return run_full_analysis(profile_dict)

@app.post("/api/v1/analysis/whatif")
def post_whatif_analysis(
    req: schemas.WhatIfRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return simulate_whatif(
        base_profile=profile.to_profile_dict(),
        extra_monthly_savings=req.extra_monthly_savings,
        return_adjustment=req.return_adjustment,
        inflation_adjustment=req.inflation_adjustment,
        retirement_age_override=req.retirement_age_override,
        loan_prepayment_monthly=req.loan_prepayment_monthly
    )

# ----------------- Chat Endpoint ----------------- #

@app.post("/api/v1/chat", response_model=schemas.ChatResponse)
def chat_with_coach(
    req: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile_dict = profile.to_profile_dict()
    analysis = run_full_analysis(profile_dict)
    
    response = coach_agent.respond(
        user_message=req.message,
        user_profile=profile_dict,
        full_analysis=analysis,
        language=req.language or "en"
    )
    return response

# ----------------- Report Download Endpoint ----------------- #

@app.get("/api/v1/report/download")
def download_report(
    format: str = Query("pdf", pattern="^(pdf|md)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile_dict = profile.to_profile_dict()
    analysis = run_full_analysis(profile_dict)
    name = current_user.full_name or "Valued Investor"
    
    if format == "md":
        content = report_agent.generate_markdown(name, profile_dict, analysis)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=ArthMitra_Plan_{name.replace(' ', '_')}.md"}
        )
    else:
        pdf_bytes = report_agent.generate_pdf(name, profile_dict, analysis)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=ArthMitra_Plan_{name.replace(' ', '_')}.pdf"}
        )

# ----------------- Health Check ----------------- #

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "disclaimer": "Educational guidance only, not SEBI-registered investment advice."
    }
