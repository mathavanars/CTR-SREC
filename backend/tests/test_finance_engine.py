"""
Unit tests for finance_engine.py.
Verifies all pure math functions and edge cases (zero income, negative savings, no loans, etc.).
"""
import pytest
from finance_engine import (
    calculate_cashflow,
    calculate_emergency_fund,
    calculate_debt_analysis,
    calculate_goals,
    calculate_asset_allocation,
    calculate_retirement,
    calculate_financial_health_score,
    generate_monthly_action_plan,
    simulate_whatif
)

def test_cashflow_normal():
    income = 100000.0
    fixed = {"rent": 25000.0, "utilities": 5000.0}
    variable = {"dining": 10000.0, "groceries": 15000.0}
    loans = [{"emi": 10000.0, "outstanding_amount": 200000.0}]
    
    result = calculate_cashflow(income, fixed, variable, loans)
    assert result["monthly_income"] == 100000.0
    assert result["total_fixed_expenses"] == 40000.0 # 25k + 5k + 10k EMI
    assert result["total_variable_expenses"] == 25000.0
    assert result["total_expenses"] == 65000.0
    assert result["savings_capacity"] == 35000.0
    assert result["savings_rate"] == 35.0
    assert result["realism_status"] == "Healthy"
    assert len(result["top_cuts"]) == 2

def test_cashflow_zero_income():
    result = calculate_cashflow(0.0, {"rent": 10000.0}, {"food": 5000.0}, [])
    assert result["monthly_income"] == 0.0
    assert result["savings_capacity"] == -15000.0
    assert result["savings_rate"] == 0.0
    assert result["realism_status"] == "No Income"

def test_cashflow_deficit():
    result = calculate_cashflow(30000.0, {"rent": 25000.0}, {"food": 10000.0}, [])
    assert result["savings_capacity"] == -5000.0
    assert result["realism_status"] == "Deficit"

def test_emergency_fund_with_dependents():
    fixed = 30000.0
    variable = 20000.0
    dependents = 2
    savings = 50000.0
    capacity = 15000.0
    
    result = calculate_emergency_fund(fixed, variable, dependents, savings, capacity)
    # Essential = 30000 + (20000 * 0.60) = 42000
    assert result["essential_monthly_expenses"] == 42000.0
    # With dependents, target is 9 months: 42000 * 9 = 378000
    assert result["target_months"] == 9
    assert result["target_amount"] == 378000.0
    assert result["current_amount"] == 50000.0
    assert result["gap"] == 328000.0
    assert result["months_covered"] == round(50000.0 / 42000.0, 1)
    assert result["months_to_fill"] > 0
    assert len(result["where_to_keep"]) == 3

def test_emergency_fund_fully_funded():
    result = calculate_emergency_fund(20000.0, 10000.0, 0, 200000.0, 20000.0)
    assert result["target_months"] == 6
    assert result["gap"] == 0.0
    assert result["status"] == "Fully Funded"

def test_debt_analysis_no_loans():
    result = calculate_debt_analysis([], 80000.0, 30000.0)
    assert result["has_loans"] is False
    assert result["total_debt"] == 0.0
    assert result["dti_ratio"] == 0.0
    assert result["dti_status"] == "Debt-Free"
    assert result["pay_this_first"] is None

def test_debt_analysis_avalanche_ranking():
    loans = [
        {"name": "Home Loan", "type": "home", "outstanding_amount": 2500000.0, "interest_rate": 8.5, "emi": 25000.0, "remaining_tenure": 180},
        {"name": "Credit Card", "type": "credit_card", "outstanding_amount": 50000.0, "interest_rate": 42.0, "emi": 4000.0, "remaining_tenure": 18},
        {"name": "Personal Loan", "type": "personal", "outstanding_amount": 200000.0, "interest_rate": 14.5, "emi": 7000.0, "remaining_tenure": 36}
    ]
    result = calculate_debt_analysis(loans, 120000.0, 40000.0)
    assert result["has_loans"] is True
    assert result["total_debt"] == 2750000.0
    assert result["total_emi"] == 36000.0
    # DTI = 36000 / 120000 = 30.0%
    assert result["dti_ratio"] == 30.0
    assert result["dti_status"] == "Healthy"
    # Avalanche: 42% credit card should be first
    assert result["loans_ranked_by_interest"][0]["name"] == "Credit Card"
    assert result["pay_this_first"]["loan_name"] == "Credit Card"
    assert result["avalanche_plan"]["months_to_debt_free"] > 0

def test_goal_analysis():
    goals = [
        {"name": "Laptop", "target_amount": 80000.0, "target_date": "2027-12", "current_saved": 10000.0, "priority": "High"},
        {"name": "House Downpayment", "target_amount": 1500000.0, "target_date": "2031-12", "current_saved": 100000.0, "priority": "Medium"}
    ]
    result = calculate_goals(goals, monthly_savings_capacity=20000.0)
    assert len(result["goals"]) == 2
    assert result["total_goals_count"] == 2
    assert result["feasible_goals_count"] >= 1
    assert result["goals"][0]["required_monthly_sip"] > 0
    assert result["goals"][0]["feasibility"] in ["On Track", "At Risk", "Unrealistic"]

def test_asset_allocation_rules():
    # 25 year old with high risk
    res_young = calculate_asset_allocation(25, "High", 30000.0, has_emergency_gap=False, goals=[])
    categories_young = {c["category"]: c["percentage"] for c in res_young["categories"]}
    assert categories_young["equity_index"] >= 50.0
    assert "real_estate_guidance" in res_young
    
    # 55 year old with low risk
    res_older = calculate_asset_allocation(55, "Low", 30000.0, has_emergency_gap=False, goals=[])
    categories_older = {c["category"]: c["percentage"] for c in res_older["categories"]}
    assert categories_older["equity_index"] <= 45.0
    assert categories_older["ppf_nps"] >= 20.0

def test_retirement_corpus():
    result = calculate_retirement(
        current_age=30,
        retirement_age=60,
        monthly_expenses=40000.0,
        current_retirement_savings=200000.0,
        current_monthly_contribution=5000.0
    )
    assert result["years_to_retirement"] == 30
    assert result["future_monthly_expense"] > 40000.0
    assert result["target_corpus"] > 10000000.0 # > 1 Crore
    assert result["additional_monthly_sip_needed"] >= 0.0

def test_financial_health_score():
    health = calculate_financial_health_score(
        savings_rate=30.0,
        emergency_months_covered=6.0,
        dti_ratio=15.0,
        investments_count=3,
        goals_feasible_ratio=100.0,
        has_insurance_or_dependents_covered=True
    )
    assert 75.0 <= health["score"] <= 100.0
    assert health["band"] in ["Good", "Excellent"]
    assert len(health["sub_scores"]) == 6

def test_action_plan_priority_order():
    cf = {"savings_capacity": 25000.0}
    em = {"gap": 100000.0, "target_months": 6, "months_covered": 2.0, "recommended_monthly_allocation": 10000.0}
    debt = {
        "has_loans": True,
        "pay_this_first": {"loan_name": "Personal Loan", "interest_rate": 15.0},
        "extra_prepay_simulated": 3000.0,
        "avalanche_plan": {"interest_saved_vs_baseline": 12000.0}
    }
    goals = {"goals": [{"name": "Car", "target_amount": 500000.0, "target_date": "2028-01", "required_monthly_sip": 8000.0}]}
    retire = {"years_to_retirement": 25, "corpus_gap": 15000000.0, "additional_monthly_sip_needed": 6000.0}
    
    plan = generate_monthly_action_plan(cf, em, debt, goals, retire)
    assert len(plan) == 5
    assert plan[0]["category"] == "Emergency Cushion"
    assert plan[1]["category"] == "Debt Payoff"
    assert plan[2]["category"] == "Risk Protection"
    assert plan[3]["category"] == "Goal Achievement"
    assert plan[4]["category"] == "Retirement Security"

def test_whatif_simulation():
    profile = {
        "monthly_income": 80000.0,
        "fixed_expenses": {"rent": 20000.0},
        "variable_expenses": {"food": 15000.0},
        "loans": [],
        "savings": 50000.0,
        "dependents": 0,
        "age": 28,
        "retirement_age": 60,
        "investments": [{"type": "mutual_fund", "current_value": 50000.0, "monthly_contribution": 5000.0}],
        "goals": [{"name": "Trip", "target_amount": 100000.0, "target_date": "2027-12", "current_saved": 0.0}]
    }
    sim = simulate_whatif(profile, extra_monthly_savings=10000.0, return_adjustment=2.0)
    assert sim["comparison"]["savings_capacity"]["delta"] == 10000.0
    assert "health_score" in sim["comparison"]
    assert "retirement_corpus_gap" in sim["comparison"]
