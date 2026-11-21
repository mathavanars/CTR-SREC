"""
Configuration and financial assumptions for ArthMitra.
All values are transparently documented as ASSUMPTIONS, never guarantees.
"""
import os

class Settings:
    # App
    PROJECT_NAME: str = "ArthMitra - AI Personal Finance Coach for India"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "arthmitra-hackathon-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Financial Assumptions (Realistic Indian Market Context)
    INFLATION_RATE_DEFAULT: float = 6.0          # Long-term CPI inflation in India (RBI target band ~4-6%)
    EDUCATION_INFLATION_RATE: float = 8.5        # Higher inflation for higher education / healthcare
    EQUITY_INDEX_RETURN: float = 12.0            # Historical Nifty 50 15-20yr CAGR assumption
    DEBT_FD_RETURN: float = 7.0                  # Fixed deposit / High-grade debt fund return
    LIQUID_CASH_RETURN: float = 4.5              # Savings account / Overnight / Liquid fund
    GOLD_RETURN: float = 8.0                     # Gold long-term hedge assumption
    PPF_NPS_RETURN: float = 8.5                  # Long-term hybrid debt/equity composite for PPF/NPS
    
    # Retirement defaults
    DEFAULT_RETIREMENT_AGE: int = 60
    DEFAULT_LIFE_EXPECTANCY: int = 85
    SAFE_WITHDRAWAL_RATE: float = 4.0            # 4% Trinity rule adapted for Indian context
    
    # Emergency Fund assumptions
    EMERGENCY_MONTHS_DEFAULT: int = 6            # 6 months for salaried with no dependents
    EMERGENCY_MONTHS_DEPENDENTS: int = 9         # 9 months for households with dependents or variable income
    
    # Health Score Weights (Total = 1.0)
    WEIGHT_SAVINGS_RATE: float = 0.20
    WEIGHT_EMERGENCY_FUND: float = 0.25
    WEIGHT_DEBT_TO_INCOME: float = 0.20
    WEIGHT_DIVERSIFICATION: float = 0.15
    WEIGHT_GOAL_PROGRESS: float = 0.10
    WEIGHT_PROTECTION_BUFFER: float = 0.10
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "fallback")  # "gemini", "openai", or "fallback"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
