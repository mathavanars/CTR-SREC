"""
models.py
SQLAlchemy models for User and UserProfile.
"""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    age = Column(Integer, default=28)
    retirement_age = Column(Integer, default=60)
    risk_appetite = Column(String(50), default="Medium") # Low / Medium / High
    dependents = Column(Integer, default=0)
    monthly_income = Column(Float, default=0.0)
    savings = Column(Float, default=0.0) # Cash and bank balance

    # JSON-encoded structures
    fixed_expenses_json = Column(Text, default="{}")
    variable_expenses_json = Column(Text, default="{}")
    investments_json = Column(Text, default="[]")
    loans_json = Column(Text, default="[]")
    goals_json = Column(Text, default="[]")
    chat_history_json = Column(Text, default="[]")
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

    def get_fixed_expenses(self) -> dict:
        try:
            return json.loads(self.fixed_expenses_json or "{}")
        except Exception:
            return {}

    def get_variable_expenses(self) -> dict:
        try:
            return json.loads(self.variable_expenses_json or "{}")
        except Exception:
            return {}

    def get_investments(self) -> list:
        try:
            return json.loads(self.investments_json or "[]")
        except Exception:
            return []

    def get_loans(self) -> list:
        try:
            return json.loads(self.loans_json or "[]")
        except Exception:
            return []

    def get_goals(self) -> list:
        try:
            return json.loads(self.goals_json or "[]")
        except Exception:
            return []
            
    def to_profile_dict(self) -> dict:
        return {
            "age": self.age,
            "retirement_age": self.retirement_age,
            "risk_appetite": self.risk_appetite,
            "dependents": self.dependents,
            "monthly_income": self.monthly_income,
            "savings": self.savings,
            "fixed_expenses": self.get_fixed_expenses(),
            "variable_expenses": self.get_variable_expenses(),
            "investments": self.get_investments(),
            "loans": self.get_loans(),
            "goals": self.get_goals()
        }
