"""
goal_agent.py
Analyzes life goals, projects inflation-adjusted targets, and evaluates feasibility.
"""
from typing import Dict, Any
from finance_engine import calculate_goals

class GoalAgent:
    def analyze(self, profile: Dict[str, Any], monthly_savings_capacity: float) -> Dict[str, Any]:
        goals = profile.get("goals", [])
        return calculate_goals(goals, monthly_savings_capacity)
