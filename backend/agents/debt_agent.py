"""
debt_agent.py
Handles debt prioritization, avalanche vs snowball payoff schedules, and prepayment analysis.
"""
from typing import Dict, Any
from finance_engine import calculate_debt_analysis

class DebtAgent:
    def analyze(self, profile: Dict[str, Any], monthly_savings_capacity: float) -> Dict[str, Any]:
        loans = profile.get("loans", [])
        income = profile.get("monthly_income", 0.0)
        return calculate_debt_analysis(loans, income, monthly_savings_capacity)
