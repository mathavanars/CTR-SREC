"""
financial_agent.py
Handles cashflow analytics, emergency fund calculations, and financial health score.
"""
from typing import Dict, Any
from finance_engine import calculate_cashflow, calculate_emergency_fund, calculate_financial_health_score

class FinancialAgent:
    def analyze(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        income = profile.get("monthly_income", 0.0)
        fixed = profile.get("fixed_expenses", {})
        variable = profile.get("variable_expenses", {})
        loans = profile.get("loans", [])
        savings = profile.get("savings", 0.0)
        dependents = profile.get("dependents", 0)
        investments = profile.get("investments", [])
        
        cashflow = calculate_cashflow(income, fixed, variable, loans)
        emergency = calculate_emergency_fund(
            cashflow["total_fixed_expenses"],
            cashflow["total_variable_expenses"],
            dependents,
            savings,
            cashflow["savings_capacity"]
        )
        
        return {
            "cashflow": cashflow,
            "emergency": emergency
        }
