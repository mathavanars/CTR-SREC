"""
investment_agent.py
Computes transparent rule-based asset allocation and retirement readiness.
"""
from typing import Dict, Any
from finance_engine import calculate_asset_allocation, calculate_retirement

class InvestmentAgent:
    def analyze(
        self,
        profile: Dict[str, Any],
        monthly_savings_capacity: float,
        has_emergency_gap: bool,
        monthly_expenses: float
    ) -> Dict[str, Any]:
        age = profile.get("age", 28)
        retire_age = profile.get("retirement_age", 60)
        risk = profile.get("risk_appetite", "Medium")
        goals = profile.get("goals", [])
        investments = profile.get("investments", [])
        
        allocation = calculate_asset_allocation(age, risk, monthly_savings_capacity, has_emergency_gap, goals)
        
        total_retire_savings = sum(
            float(i.get("current_value", 0.0))
            for i in investments
            if i.get("type") in ["ppf_nps", "mutual_fund", "stocks", "epf", "fd"]
        )
        total_retire_sip = sum(
            float(i.get("monthly_contribution", 0.0))
            for i in investments
            if i.get("type") in ["ppf_nps", "mutual_fund", "stocks", "epf"]
        )
        
        retirement = calculate_retirement(
            current_age=age,
            retirement_age=retire_age,
            monthly_expenses=monthly_expenses,
            current_retirement_savings=total_retire_savings,
            current_monthly_contribution=total_retire_sip
        )
        
        return {
            "allocation": allocation,
            "retirement": retirement
        }
