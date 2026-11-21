"""
finance_engine.py
Pure financial calculation engine for ArthMitra.
All math and deterministic logic lives here. No LLM prompts or UI code.
Fully typed, pure functions with edge-case handling.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import math
from config import settings

def calculate_cashflow(
    monthly_income: float,
    fixed_expenses: Dict[str, float],
    variable_expenses: Dict[str, float],
    loans: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes monthly cashflow, savings capacity, savings rate, and expense breakdown.
    Handles edge cases: zero income, negative savings capacity, empty expense dicts.
    """
    income = max(0.0, float(monthly_income))
    
    total_fixed_base = sum(max(0.0, float(v)) for v in fixed_expenses.values())
    loan_emis = sum(max(0.0, float(loan.get("emi", 0.0))) for loan in loans)
    total_fixed = total_fixed_base + loan_emis
    
    total_variable = sum(max(0.0, float(v)) for v in variable_expenses.values())
    total_expenses = total_fixed + total_variable
    
    savings_capacity = income - total_expenses
    savings_rate = (savings_capacity / income * 100.0) if income > 0 else 0.0
    
    # Realism check
    if income == 0:
        realism_status = "No Income"
        realism_note = "Income is recorded as zero. Please update income to receive an active cashflow plan."
    elif savings_capacity < 0:
        realism_status = "Deficit"
        realism_note = f"Monthly spending exceeds income by ₹{abs(savings_capacity):,.0f}. Urgent budget rationalization needed."
    elif savings_rate < 15.0:
        realism_status = "Tight"
        realism_note = f"Savings rate of {savings_rate:.1f}% is below the 20% benchmark. Trimming variable expenses can boost capacity."
    elif savings_rate <= 40.0:
        realism_status = "Healthy"
        realism_note = f"Solid savings rate of {savings_rate:.1f}%. Well-aligned with the 50/30/20 guideline."
    else:
        realism_status = "Exceptional"
        realism_note = f"Outstanding savings rate of {savings_rate:.1f}%. Strong wealth-building velocity."
        
    # Top 3 areas to cut (variable expenses prioritized)
    sorted_cuts = sorted(
        [(k, max(0.0, float(v))) for k, v in variable_expenses.items() if float(v) > 0],
        key=lambda x: x[1],
        reverse=True
    )
    top_cuts = []
    for category, amount in sorted_cuts[:3]:
        # Suggest 15% to 25% realistic trimming
        trim_percentage = 20.0
        potential_saving = round(amount * (trim_percentage / 100.0), 0)
        top_cuts.append({
            "category": category.replace("_", " ").title(),
            "current_spend": amount,
            "trim_percentage": trim_percentage,
            "potential_saving": potential_saving,
            "tip": f"Trimming discretionary {category.replace('_', ' ')} by {int(trim_percentage)}% frees up ₹{potential_saving:,.0f}/month."
        })
        
    # Expense breakdown structure for UI charts
    breakdown = []
    for k, v in fixed_expenses.items():
        if float(v) > 0:
            breakdown.append({"category": f"Fixed: {k.replace('_', ' ').title()}", "amount": float(v), "type": "Fixed"})
    if loan_emis > 0:
        breakdown.append({"category": "Fixed: Loan EMIs", "amount": loan_emis, "type": "Fixed"})
    for k, v in variable_expenses.items():
        if float(v) > 0:
            breakdown.append({"category": f"Variable: {k.replace('_', ' ').title()}", "amount": float(v), "type": "Variable"})
            
    return {
        "monthly_income": income,
        "total_fixed_expenses": round(total_fixed, 2),
        "total_variable_expenses": round(total_variable, 2),
        "loan_emis": round(loan_emis, 2),
        "total_expenses": round(total_expenses, 2),
        "savings_capacity": round(savings_capacity, 2),
        "savings_rate": round(savings_rate, 2),
        "realism_status": realism_status,
        "realism_note": realism_note,
        "top_cuts": top_cuts,
        "expense_breakdown": breakdown
    }

def calculate_emergency_fund(
    monthly_fixed_expenses: float,
    monthly_variable_expenses: float,
    dependents: int,
    current_savings: float,
    monthly_savings_capacity: float,
    has_irregular_income: bool = False
) -> Dict[str, Any]:
    """
    Emergency Fund Planning:
    Target = 6 months essential expenses (or 9 months if dependents > 0 or irregular income).
    Essential expenses = 100% of fixed expenses + 60% of variable expenses (survival budget).
    """
    essential_monthly = monthly_fixed_expenses + (monthly_variable_expenses * 0.60)
    essential_monthly = max(1000.0, essential_monthly)
    
    target_months = settings.EMERGENCY_MONTHS_DEPENDENTS if (dependents > 0 or has_irregular_income) else settings.EMERGENCY_MONTHS_DEFAULT
    target_amount = round(essential_monthly * target_months, 2)
    current_liquid = max(0.0, float(current_savings))
    
    gap = max(0.0, target_amount - current_liquid)
    months_covered = (current_liquid / essential_monthly) if essential_monthly > 0 else 0.0
    
    # Allocation pace
    if gap <= 0:
        months_to_fill = 0
        recommended_monthly_allocation = 0.0
        status = "Fully Funded"
        status_note = f"You have {months_covered:.1f} months of essential expenses safely parked. Excellent buffer!"
    elif monthly_savings_capacity <= 0:
        months_to_fill = 999
        recommended_monthly_allocation = 0.0
        status = "Critical Gap"
        status_note = "Your emergency cushion is underfunded, and current cashflow has no surplus. Budget trimming required first."
    else:
        # Prioritize 40% of savings capacity towards emergency fund until full
        recommended_monthly_allocation = min(gap, max(monthly_savings_capacity * 0.40, min(monthly_savings_capacity, 5000.0)))
        months_to_fill = math.ceil(gap / recommended_monthly_allocation) if recommended_monthly_allocation > 0 else 999
        status = "Building Cushion"
        status_note = f"Current liquidity covers {months_covered:.1f} months. Target is {target_months} months (₹{target_amount:,.0f})."

    where_to_keep = [
        {"share": "30%", "vehicle": "High-Yield Bank Savings Account", "reason": "Immediate ATM / UPI accessibility for same-day medical/car needs."},
        {"share": "40%", "vehicle": "Overnight / Liquid Mutual Fund", "reason": "T+1 redemption with indexation/interest safety and no lock-in penalty."},
        {"share": "30%", "vehicle": "Auto-Sweep / Short-Term Bank FD", "reason": "Higher interest (~6.5-7%) with instant breakability via netbanking."}
    ]

    return {
        "target_months": target_months,
        "essential_monthly_expenses": round(essential_monthly, 2),
        "target_amount": round(target_amount, 2),
        "current_amount": round(current_liquid, 2),
        "months_covered": round(months_covered, 1),
        "gap": round(gap, 2),
        "months_to_fill": months_to_fill,
        "recommended_monthly_allocation": round(recommended_monthly_allocation, 2),
        "status": status,
        "status_note": status_note,
        "where_to_keep": where_to_keep
    }

def calculate_debt_analysis(
    loans: List[Dict[str, Any]],
    monthly_income: float,
    monthly_savings_capacity: float
) -> Dict[str, Any]:
    """
    Debt analysis:
    - Debt to Income (DTI) ratio
    - Ranking by interest rate (descending)
    - Avalanche vs Snowball payoff comparison
    - Interest saved by prepaying an extra 10% or ₹2,000/mo
    - Clear 'Pay this first' recommendation
    """
    income = max(1.0, float(monthly_income))
    valid_loans = []
    
    for idx, raw in enumerate(loans):
        bal = max(0.0, float(raw.get("outstanding_amount", 0.0)))
        rate = max(0.0, float(raw.get("interest_rate", 0.0)))
        emi = max(0.0, float(raw.get("emi", 0.0)))
        tenure = max(0, int(raw.get("remaining_tenure", 0)))
        loan_type = raw.get("type", f"Loan {idx + 1}")
        
        # If emi is missing or 0 but balance & tenure exist, calculate standard EMI
        if emi == 0 and bal > 0 and tenure > 0:
            monthly_r = (rate / 100.0) / 12.0
            if monthly_r > 0:
                emi = bal * monthly_r * ((1 + monthly_r)**tenure) / (((1 + monthly_r)**tenure) - 1)
            else:
                emi = bal / tenure
        
        if bal > 0:
            valid_loans.append({
                "id": str(raw.get("id", idx + 1)),
                "name": raw.get("name", loan_type.replace("_", " ").title()),
                "type": loan_type,
                "outstanding_amount": round(bal, 2),
                "interest_rate": round(rate, 2),
                "emi": round(emi, 2),
                "remaining_tenure": tenure
            })
            
    total_debt = sum(l["outstanding_amount"] for l in valid_loans)
    total_emi = sum(l["emi"] for l in valid_loans)
    dti_ratio = (total_emi / income) * 100.0
    
    # DTI status
    if total_debt == 0:
        dti_status = "Debt-Free"
        dti_note = "Congratulations! You have zero loan obligations. 100% of your savings capacity can compound."
    elif dti_ratio <= 30.0:
        dti_status = "Healthy"
        dti_note = f"DTI is {dti_ratio:.1f}%, comfortably under the prudent 35% threshold."
    elif dti_ratio <= 45.0:
        dti_status = "Moderate"
        dti_note = f"DTI is {dti_ratio:.1f}%. Loan EMIs consume a significant share of income; avoid new credit."
    else:
        dti_status = "Critical Risk"
        dti_note = f"DTI is {dti_ratio:.1f}%. High risk of debt trap. Aggressive loan payoff is strongly recommended."

    if not valid_loans:
        return {
            "has_loans": False,
            "total_debt": 0.0,
            "total_emi": 0.0,
            "dti_ratio": 0.0,
            "dti_status": "Debt-Free",
            "dti_note": "Zero debt obligations recorded.",
            "loans_ranked_by_interest": [],
            "avalanche_plan": {},
            "snowball_plan": {},
            "prepayment_comparison": {},
            "pay_this_first": None
        }

    # Rank by interest rate descending (Avalanche)
    avalanche_ranked = sorted(valid_loans, key=lambda x: x["interest_rate"], reverse=True)
    # Rank by balance ascending (Snowball)
    snowball_ranked = sorted(valid_loans, key=lambda x: x["outstanding_amount"])
    
    # Avalanche vs Snowball simulation
    extra_prepay = max(1000.0, min(monthly_savings_capacity * 0.30 if monthly_savings_capacity > 0 else 1000.0, 10000.0))
    
    def simulate_payoff(ranked_list: List[Dict[str, Any]], extra_monthly: float):
        loans_state = [dict(l) for l in ranked_list]
        month = 0
        total_interest_paid = 0.0
        max_months = 360 # 30 yr limit
        
        while any(l["outstanding_amount"] > 0 for l in loans_state) and month < max_months:
            month += 1
            available_extra = extra_monthly
            
            # 1. Apply monthly interest and regular EMI
            for l in loans_state:
                if l["outstanding_amount"] <= 0:
                    continue
                monthly_rate = (l["interest_rate"] / 100.0) / 12.0
                interest = l["outstanding_amount"] * monthly_rate
                total_interest_paid += interest
                l["outstanding_amount"] += interest
                
                payment = min(l["emi"], l["outstanding_amount"])
                l["outstanding_amount"] -= payment
                
            # 2. Apply extra prepayment to target loan
            for l in loans_state:
                if l["outstanding_amount"] > 0 and available_extra > 0:
                    prepay = min(available_extra, l["outstanding_amount"])
                    l["outstanding_amount"] -= prepay
                    available_extra -= prepay
                    break
                    
        return {"months": month, "total_interest": round(total_interest_paid, 2)}

    base_sim = simulate_payoff(avalanche_ranked, extra_monthly=0.0)
    avalanche_sim = simulate_payoff(avalanche_ranked, extra_monthly=extra_prepay)
    snowball_sim = simulate_payoff(snowball_ranked, extra_monthly=extra_prepay)
    
    avalanche_interest_saved = max(0.0, base_sim["total_interest"] - avalanche_sim["total_interest"])
    snowball_interest_saved = max(0.0, base_sim["total_interest"] - snowball_sim["total_interest"])
    
    # Pay this first recommendation
    highest_rate_loan = avalanche_ranked[0]
    pay_first_rec = {
        "loan_name": highest_rate_loan["name"],
        "loan_type": highest_rate_loan["type"],
        "interest_rate": highest_rate_loan["interest_rate"],
        "outstanding_amount": highest_rate_loan["outstanding_amount"],
        "monthly_emi": highest_rate_loan["emi"],
        "reason": f"{highest_rate_loan['name']} charges the highest annual rate at {highest_rate_loan['interest_rate']}%. Clearing this first minimizes cumulative interest drag (Mathematical Avalanche method)."
    }

    return {
        "has_loans": True,
        "total_debt": round(total_debt, 2),
        "total_emi": round(total_emi, 2),
        "dti_ratio": round(dti_ratio, 2),
        "dti_status": dti_status,
        "dti_note": dti_note,
        "loans_ranked_by_interest": avalanche_ranked,
        "extra_prepay_simulated": round(extra_prepay, 2),
        "avalanche_plan": {
            "strategy": "Debt Avalanche (Mathematical Optimal)",
            "order": [l["name"] for l in avalanche_ranked],
            "months_to_debt_free": avalanche_sim["months"],
            "total_interest": avalanche_sim["total_interest"],
            "interest_saved_vs_baseline": round(avalanche_interest_saved, 2),
            "description": "Tackle the highest interest loans first. Saves the maximum rupees in interest."
        },
        "snowball_plan": {
            "strategy": "Debt Snowball (Psychological Momentum)",
            "order": [l["name"] for l in snowball_ranked],
            "months_to_debt_free": snowball_sim["months"],
            "total_interest": snowball_sim["total_interest"],
            "interest_saved_vs_baseline": round(snowball_interest_saved, 2),
            "description": "Eliminate the smallest balances first to score quick psychological wins."
        },
        "prepayment_comparison": {
            "baseline_months": base_sim["months"],
            "baseline_interest": base_sim["total_interest"],
            "extra_monthly_prepayment": round(extra_prepay, 2),
            "recommended_strategy": "Avalanche" if avalanche_interest_saved >= snowball_interest_saved else "Snowball",
            "net_rupees_saved": round(max(avalanche_interest_saved, snowball_interest_saved), 2)
        },
        "pay_this_first": pay_first_rec
    }

def calculate_goals(
    goals: List[Dict[str, Any]],
    monthly_savings_capacity: float,
    general_inflation: float = settings.INFLATION_RATE_DEFAULT,
    expected_return: float = settings.EQUITY_INDEX_RETURN
) -> Dict[str, Any]:
    """
    Goal feasibility analysis:
    - Adjusts target amount for inflation based on target date horizon
    - Calculates required monthly SIP using compound interest PMT formula:
      FV = PMT * [((1 + r)^n - 1) / r] * (1 + r)
    - Determines feasibility: On Track / At Risk / Unrealistic
    - Computes projected completion date and recommended fix
    """
    now = datetime.now()
    analyzed_goals = []
    total_required_monthly = 0.0
    
    for idx, raw_goal in enumerate(goals):
        name = raw_goal.get("name", f"Goal {idx + 1}")
        target_amount = max(1000.0, float(raw_goal.get("target_amount", 0.0)))
        current_corpus = max(0.0, float(raw_goal.get("current_saved", 0.0)))
        priority = raw_goal.get("priority", "Medium").capitalize()
        category = raw_goal.get("category", "General")
        
        # Horizon calculation
        target_date_str = raw_goal.get("target_date", "")
        months_horizon = 36 # default 3 yrs if parse fails
        target_year = now.year + 3
        if target_date_str:
            try:
                # Handle YYYY-MM or YYYY-MM-DD
                parts = target_date_str.split("-")
                t_year = int(parts[0])
                t_month = int(parts[1]) if len(parts) > 1 else 12
                target_year = t_year
                months_horizon = max(1, (t_year - now.year) * 12 + (t_month - now.month))
            except Exception:
                months_horizon = 36
                
        years_horizon = months_horizon / 12.0
        
        # Use education inflation for higher ed / child goals, otherwise general
        infl_rate = settings.EDUCATION_INFLATION_RATE if "educat" in name.lower() or "child" in name.lower() else general_inflation
        
        # Inflation-adjusted future target amount
        future_target_amount = target_amount * ((1.0 + (infl_rate / 100.0)) ** years_horizon)
        
        # Assumed annualized return depending on horizon:
        # < 3 yrs: Safe debt / liquid (6%)
        # 3-5 yrs: Hybrid (9%)
        # > 5 yrs: Equity index (12%)
        if years_horizon < 3.0:
            assigned_return = settings.DEBT_FD_RETURN
        elif years_horizon <= 5.0:
            assigned_return = 9.0
        else:
            assigned_return = expected_return
            
        r_monthly = (assigned_return / 100.0) / 12.0
        
        # Future value of current corpus
        fv_current = current_corpus * ((1.0 + r_monthly) ** months_horizon)
        remaining_future_target = max(0.0, future_target_amount - fv_current)
        
        if remaining_future_target == 0:
            required_monthly = 0.0
        elif r_monthly > 0:
            # SIP annuity formula: PMT = FV * r / [((1 + r)^n - 1) * (1 + r)]
            factor = (((1.0 + r_monthly) ** months_horizon) - 1.0) * (1.0 + r_monthly)
            required_monthly = (remaining_future_target * r_monthly) / factor
        else:
            required_monthly = remaining_future_target / months_horizon
            
        required_monthly = round(required_monthly, 2)
        total_required_monthly += required_monthly
        
        analyzed_goals.append({
            "id": str(raw_goal.get("id", idx + 1)),
            "name": name,
            "category": category,
            "priority": priority,
            "target_amount": round(target_amount, 2),
            "future_target_amount": round(future_target_amount, 2),
            "current_saved": round(current_corpus, 2),
            "target_date": target_date_str or f"{target_year}-12",
            "months_horizon": months_horizon,
            "years_horizon": round(years_horizon, 1),
            "inflation_applied": infl_rate,
            "assumed_return": assigned_return,
            "required_monthly_sip": required_monthly
        })
        
    # Evaluate feasibility against actual monthly savings capacity
    # Priority sorting: High > Medium > Low
    priority_map = {"High": 1, "Medium": 2, "Low": 3}
    analyzed_goals.sort(key=lambda x: (priority_map.get(x["priority"], 2), x["months_horizon"]))
    
    available_pool = max(0.0, monthly_savings_capacity)
    feasible_count = 0
    
    for g in analyzed_goals:
        req = g["required_monthly_sip"]
        if req == 0:
            g["feasibility"] = "On Track"
            g["feasibility_badge"] = "success"
            g["status_message"] = "Fully funded with existing savings trajectory."
            g["suggested_fix"] = "Keep corpus invested in aligned low-risk instrument."
            feasible_count += 1
        elif available_pool >= req:
            g["feasibility"] = "On Track"
            g["feasibility_badge"] = "success"
            g["status_message"] = f"Requires ₹{req:,.0f}/mo, covered by current savings capacity."
            g["suggested_fix"] = f"Set up automated SIP of ₹{req:,.0f}/mo immediately after salary credit."
            available_pool -= req
            feasible_count += 1
        elif available_pool > 0:
            # At risk
            shortfall = req - available_pool
            g["feasibility"] = "At Risk"
            g["feasibility_badge"] = "warning"
            g["status_message"] = f"Monthly shortfall of ₹{shortfall:,.0f}/mo under current capacity."
            
            # Suggest fix: extend horizon or boost savings
            r_mo = (g["assumed_return"] / 100.0) / 12.0
            if available_pool > 0 and r_mo > 0:
                # Solve for n with available_pool: FV = PMT * [((1+r)^n - 1)/r] * (1+r)
                # (1+r)^n = 1 + (FV * r) / (PMT * (1+r))
                val = 1.0 + (g["future_target_amount"] * r_mo) / (available_pool * (1.0 + r_mo))
                if val > 0:
                    needed_months = math.ceil(math.log(val) / math.log(1.0 + r_mo))
                    extra_months = max(1, needed_months - g["months_horizon"])
                    g["suggested_fix"] = f"Extend target horizon by ~{extra_months} months, or trim expenses by ₹{shortfall:,.0f}/month."
                else:
                    g["suggested_fix"] = f"Increase savings by ₹{shortfall:,.0f}/month or adjust target down."
            else:
                g["suggested_fix"] = f"Increase savings by ₹{shortfall:,.0f}/month."
            available_pool = 0.0
        else:
            g["feasibility"] = "Unrealistic"
            g["feasibility_badge"] = "danger"
            g["status_message"] = f"Zero unallocated monthly savings remaining for this goal."
            g["suggested_fix"] = f"Postpone this lower-priority goal until higher priority loans and emergency cushions are secured."
            
    return {
        "goals": analyzed_goals,
        "total_required_monthly_sip": round(total_required_monthly, 2),
        "total_goals_count": len(analyzed_goals),
        "feasible_goals_count": feasible_count,
        "goals_on_track_ratio": round((feasible_count / len(analyzed_goals)) * 100.0, 1) if analyzed_goals else 100.0
    }

def calculate_asset_allocation(
    age: int,
    risk_appetite: str,
    monthly_savings_capacity: float,
    has_emergency_gap: bool,
    goals: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transparent rule-based asset allocation across categories.
    Rules:
    - Age-adjusted equity baseline: 100 - age
    - Risk adjustments:
        - Low: base - 15%, max equity capped at 45%
        - Medium: base, max equity capped at 65%
        - High: base + 15%, max equity capped at 80%
    - Emergency priority: If emergency fund has a gap, assign 25-40% of monthly savings directly to Emergency/Liquid.
    - Gold allocation: 5-10% systematic allocation as rupee/inflation shock absorber.
    - PPF / NPS: 15-20% for tax-advantaged sovereign guaranteed retirement.
    - FD / Debt / Liquid: absorbs balance.
    - Never recommends specific stocks or fund houses.
    - Explains real estate illiquidity constraint.
    """
    clean_age = max(18, min(80, int(age)))
    risk = risk_appetite.capitalize() if risk_appetite else "Medium"
    
    # 1. Base equity target
    if risk == "Low":
        target_equity = max(15.0, min(45.0, (90.0 - clean_age)))
        gold_pct = 8.0
        retirement_debt_pct = 25.0
    elif risk == "High":
        target_equity = max(40.0, min(80.0, (115.0 - clean_age)))
        gold_pct = 5.0
        retirement_debt_pct = 15.0
    else: # Medium
        target_equity = max(30.0, min(65.0, (100.0 - clean_age)))
        gold_pct = 7.0
        retirement_debt_pct = 20.0
        
    # 2. Emergency cushion consideration
    if has_emergency_gap:
        emergency_liquid_pct = 30.0
        # Scale back equity and retirement proportionally
        scale = (100.0 - emergency_liquid_pct - gold_pct) / (target_equity + retirement_debt_pct + 10.0)
        equity_pct = round(target_equity * scale, 1)
        debt_fd_pct = round(10.0 * scale, 1)
        retirement_pct = round(retirement_debt_pct * scale, 1)
    else:
        emergency_liquid_pct = 10.0
        remainder = 100.0 - (target_equity + gold_pct + retirement_debt_pct + emergency_liquid_pct)
        equity_pct = target_equity
        retirement_pct = retirement_debt_pct
        debt_fd_pct = max(5.0, remainder)
        
    # Normalize to 100%
    total = emergency_liquid_pct + debt_fd_pct + equity_pct + gold_pct + retirement_pct
    emergency_liquid_pct = round((emergency_liquid_pct / total) * 100.0, 1)
    debt_fd_pct = round((debt_fd_pct / total) * 100.0, 1)
    equity_pct = round((equity_pct / total) * 100.0, 1)
    gold_pct = round((gold_pct / total) * 100.0, 1)
    retirement_pct = round(100.0 - (emergency_liquid_pct + debt_fd_pct + equity_pct + gold_pct), 1)
    
    capacity = max(0.0, monthly_savings_capacity)
    
    categories = [
        {
            "category": "equity_index",
            "name": "Equity Index Funds (Nifty 50 / Nifty 500)",
            "percentage": equity_pct,
            "monthly_amount": round(capacity * (equity_pct / 100.0), 0),
            "expected_return": f"{settings.EQUITY_INDEX_RETURN}% p.a.",
            "purpose": "Long-term compounding to beat 6% inflation. Low expense-ratio passive index funds eliminate fund manager selection risk."
        },
        {
            "category": "ppf_nps",
            "name": "Retirement Vehicles (PPF / NPS / EPF)",
            "percentage": retirement_pct,
            "monthly_amount": round(capacity * (retirement_pct / 100.0), 0),
            "expected_return": f"{settings.PPF_NPS_RETURN}% p.a.",
            "purpose": "Lock-in discipline with tax advantages (Section 80C & 80CCD). Creates sovereign-backed retirement security."
        },
        {
            "category": "fd_debt",
            "name": "Fixed Deposits & High-Quality Debt Funds",
            "percentage": debt_fd_pct,
            "monthly_amount": round(capacity * (debt_fd_pct / 100.0), 0),
            "expected_return": f"{settings.DEBT_FD_RETURN}% p.a.",
            "purpose": "Capital protection for medium-term goals (2-4 years) with predictable yields and low volatility."
        },
        {
            "category": "emergency_liquid",
            "name": "Liquid & Overnight Funds / Savings",
            "percentage": emergency_liquid_pct,
            "monthly_amount": round(capacity * (emergency_liquid_pct / 100.0), 0),
            "expected_return": f"{settings.LIQUID_CASH_RETURN}% p.a.",
            "purpose": "Immediate access reserve for medical emergencies and cashflow buffering without market fluctuation."
        },
        {
            "category": "gold",
            "name": "Sovereign Gold Bonds / Digital Gold",
            "percentage": gold_pct,
            "monthly_amount": round(capacity * (gold_pct / 100.0), 0),
            "expected_return": f"{settings.GOLD_RETURN}% p.a.",
            "purpose": "Non-correlated defensive hedge against geopolitical volatility and currency depreciation."
        }
    ]
    
    rationale = (
        f"Based on your age ({clean_age}) and {risk} risk tolerance: Your equity allocation is established at {equity_pct}% "
        f"using the standard '100 minus age' formula adjusted for risk profile. "
        f"{'Because an emergency fund gap exists, liquid savings are temporarily boosted to build resilience first. ' if has_emergency_gap else ''}"
        f"Real estate is excluded from monthly liquid SIPs because property purchases require substantial illiquid capital and leverage, "
        f"making it unsuitable for foundational wealth accumulation."
    )
    
    real_estate_guidance = {
        "status": "Unsuitable for Early Wealth Creation",
        "reason": "Real estate transactions incur 6-8% stamp duty and registration friction, have zero divisibility, low rental yields (2-3% in urban India), and require heavy debt (EMIs). First establish a diversified liquid portfolio before committing capital to immovable property."
    }

    return {
        "categories": categories,
        "rationale": rationale,
        "real_estate_guidance": real_estate_guidance,
        "risk_appetite_applied": risk,
        "age_applied": clean_age
    }

def calculate_retirement(
    current_age: int,
    retirement_age: int,
    monthly_expenses: float,
    current_retirement_savings: float,
    current_monthly_contribution: float,
    inflation_rate: float = settings.INFLATION_RATE_DEFAULT,
    pre_retirement_return: float = 11.0,
    post_retirement_return: float = 7.5,
    safe_withdrawal_rate: float = settings.SAFE_WITHDRAWAL_RATE
) -> Dict[str, Any]:
    """
    Retirement corpus calculation:
    - Calculates future annual expense at retirement age adjusted for inflation
    - Uses safe withdrawal formula and longevity buffer (up to age 85)
    - Projects existing corpus & existing SIPs to retirement date
    - Computes shortfall and additional monthly SIP needed
    """
    age = max(18, min(75, int(current_age)))
    retire_age = max(age + 1, min(80, int(retirement_age)))
    years_to_retire = max(1, retire_age - age)
    years_in_retire = max(10, settings.DEFAULT_LIFE_EXPECTANCY - retire_age)
    
    monthly_exp = max(5000.0, float(monthly_expenses))
    current_savings = max(0.0, float(current_retirement_savings))
    current_sip = max(0.0, float(current_monthly_contribution))
    
    # Future monthly expenses at retirement date
    inflation_factor = (1.0 + (inflation_rate / 100.0)) ** years_to_retire
    future_monthly_expense = monthly_exp * inflation_factor
    future_annual_expense = future_monthly_expense * 12.0
    
    # Required corpus at retirement:
    # 4% safe withdrawal rate means corpus = 25 * Annual Expenses
    corpus_via_swr = future_annual_expense * (100.0 / safe_withdrawal_rate)
    
    # Real return in retirement annuity check:
    real_post_retire_rate = ((1.0 + post_retirement_return/100.0) / (1.0 + inflation_rate/100.0)) - 1.0
    if abs(real_post_retire_rate) > 0.001:
        annuity_factor = (1.0 - ((1.0 + real_post_retire_rate) ** (-years_in_retire))) / real_post_retire_rate
        corpus_via_annuity = future_annual_expense * annuity_factor
    else:
        corpus_via_annuity = future_annual_expense * years_in_retire
        
    # We take the more conservative between SWR and life-annuity
    target_corpus = max(corpus_via_swr, corpus_via_annuity)
    
    # Project existing savings to retirement
    r_pre_monthly = (pre_retirement_return / 100.0) / 12.0
    months_to_retire = years_to_retire * 12
    
    projected_from_lumpsum = current_savings * ((1.0 + r_pre_monthly) ** months_to_retire)
    
    if r_pre_monthly > 0 and current_sip > 0:
        factor = (((1.0 + r_pre_monthly) ** months_to_retire) - 1.0) * (1.0 + r_pre_monthly)
        projected_from_sip = (current_sip * factor) / r_pre_monthly
    else:
        projected_from_sip = current_sip * months_to_retire
        
    projected_total = projected_from_lumpsum + projected_from_sip
    corpus_gap = max(0.0, target_corpus - projected_total)
    
    # Required extra monthly SIP to bridge the gap
    if corpus_gap > 0 and r_pre_monthly > 0:
        factor = (((1.0 + r_pre_monthly) ** months_to_retire) - 1.0) * (1.0 + r_pre_monthly)
        additional_monthly_sip = (corpus_gap * r_pre_monthly) / factor
    elif corpus_gap > 0:
        additional_monthly_sip = corpus_gap / months_to_retire
    else:
        additional_monthly_sip = 0.0
        
    readiness_percentage = min(100.0, (projected_total / target_corpus * 100.0)) if target_corpus > 0 else 100.0
    
    return {
        "current_age": age,
        "retirement_age": retire_age,
        "years_to_retirement": years_to_retire,
        "years_in_retirement": years_in_retire,
        "current_monthly_expense": round(monthly_exp, 2),
        "future_monthly_expense": round(future_monthly_expense, 2),
        "future_annual_expense": round(future_annual_expense, 2),
        "target_corpus": round(target_corpus, 2),
        "projected_corpus_at_current_pace": round(projected_total, 2),
        "corpus_gap": round(corpus_gap, 2),
        "readiness_percentage": round(readiness_percentage, 1),
        "current_monthly_sip": round(current_sip, 2),
        "additional_monthly_sip_needed": round(additional_monthly_sip, 2),
        "assumptions": {
            "inflation_rate": inflation_rate,
            "pre_retirement_cagr": pre_retirement_return,
            "post_retirement_cagr": post_retirement_return,
            "safe_withdrawal_rate": safe_withdrawal_rate,
            "life_expectancy": settings.DEFAULT_LIFE_EXPECTANCY
        }
    }

def calculate_financial_health_score(
    savings_rate: float,
    emergency_months_covered: float,
    dti_ratio: float,
    investments_count: int,
    goals_feasible_ratio: float,
    has_insurance_or_dependents_covered: bool
) -> Dict[str, Any]:
    """
    Calculates weighted Financial Health Score (0-100).
    Components:
    1. Savings Rate (20%): >=30% = 100, 20% = 80, 10% = 50, <=0% = 0
    2. Emergency Fund (25%): >=6 mos = 100, 3 mos = 60, 1 mo = 30, 0 = 0
    3. Debt-to-Income (20%): 0% = 100, <=25% = 85, <=40% = 55, >50% = 10
    4. Diversification (15%): >=4 asset types = 100, 3 = 80, 2 = 60, 1 = 30, 0 = 0
    5. Goal Progress (10%): ratio of feasible goals * 100
    6. Protection / Dependents Buffer (10%): insurance in place = 100, else 40
    """
    # 1. Savings score
    if savings_rate >= 35.0:
        s_score = 100.0
        s_reason = f"Excellent savings rate of {savings_rate:.1f}%, beating the 30% golden benchmark."
    elif savings_rate >= 20.0:
        s_score = 80.0 + ((savings_rate - 20.0) / 15.0) * 20.0
        s_reason = f"Healthy savings rate of {savings_rate:.1f}%, compliant with standard 50/30/20 guidelines."
    elif savings_rate >= 10.0:
        s_score = 50.0 + ((savings_rate - 10.0) / 10.0) * 30.0
        s_reason = f"Moderate savings rate of {savings_rate:.1f}%. Scope to trim variable spending."
    elif savings_rate > 0:
        s_score = (savings_rate / 10.0) * 50.0
        s_reason = f"Low savings rate of {savings_rate:.1f}%. Living paycheck to paycheck risk."
    else:
        s_score = 0.0
        s_reason = "Zero or negative savings rate. Expenses exceed income."
    s_score = max(0.0, min(100.0, s_score))
    
    # 2. Emergency fund score
    if emergency_months_covered >= 6.0:
        e_score = 100.0
        e_reason = f"Superb liquidity! {emergency_months_covered:.1f} months of expenses safely banked."
    elif emergency_months_covered >= 3.0:
        e_score = 60.0 + ((emergency_months_covered - 3.0) / 3.0) * 40.0
        e_reason = f"Decent safety cushion ({emergency_months_covered:.1f} months), but target is 6+ months."
    elif emergency_months_covered >= 1.0:
        e_score = 30.0 + ((emergency_months_covered - 1.0) / 2.0) * 30.0
        e_reason = f"Vulnerable cushion ({emergency_months_covered:.1f} months). Sudden medical/job shock could trigger debt."
    else:
        e_score = max(5.0, emergency_months_covered * 30.0)
        e_reason = "Urgent: Less than 1 month of essential expenses saved."
    e_score = max(0.0, min(100.0, e_score))
    
    # 3. Debt score
    if dti_ratio == 0:
        d_score = 100.0
        d_reason = "Debt-free! Zero loan EMIs eating into monthly cash flow."
    elif dti_ratio <= 20.0:
        d_score = 90.0 - (dti_ratio / 20.0) * 15.0
        d_reason = f"Low debt burden ({dti_ratio:.1f}% DTI). Well within safe banking limits."
    elif dti_ratio <= 40.0:
        d_score = 75.0 - ((dti_ratio - 20.0) / 20.0) * 30.0
        d_reason = f"Moderate debt burden ({dti_ratio:.1f}% DTI). Prioritize prepayment before new loans."
    elif dti_ratio <= 55.0:
        d_score = 45.0 - ((dti_ratio - 40.0) / 15.0) * 25.0
        d_reason = f"High debt burden ({dti_ratio:.1f}% DTI). High portion of income locked into interest."
    else:
        d_score = 10.0
        d_reason = f"Severe debt distress ({dti_ratio:.1f}% DTI). Urgent debt restructuring needed."
    d_score = max(0.0, min(100.0, d_score))
    
    # 4. Diversification score
    if investments_count >= 4:
        div_score = 100.0
        div_reason = f"High portfolio resilience across {investments_count} diverse asset classes."
    elif investments_count == 3:
        div_score = 80.0
        div_reason = "Good diversification across 3 asset classes (e.g., Equity, Debt, Gold)."
    elif investments_count == 2:
        div_score = 60.0
        div_reason = "Moderate diversification (2 asset classes). Adding equity or liquid assets recommended."
    elif investments_count == 1:
        div_score = 35.0
        div_reason = "Concentration risk: 100% of wealth parked in a single asset type."
    else:
        div_score = 10.0
        div_reason = "No active investments identified yet."
        
    # 5. Goal progress score
    g_score = max(0.0, min(100.0, float(goals_feasible_ratio)))
    g_reason = f"{g_score:.0f}% of designated life goals are realistically on track."
    
    # 6. Protection buffer score
    if has_insurance_or_dependents_covered:
        p_score = 100.0
        p_reason = "Adequate insurance protection in place against health & life risks."
    else:
        p_score = 45.0
        p_reason = "No term insurance / health buffer identified. Dependents could be financially vulnerable."
        
    # Weighted total
    total_score = (
        (s_score * settings.WEIGHT_SAVINGS_RATE) +
        (e_score * settings.WEIGHT_EMERGENCY_FUND) +
        (d_score * settings.WEIGHT_DEBT_TO_INCOME) +
        (div_score * settings.WEIGHT_DIVERSIFICATION) +
        (g_score * settings.WEIGHT_GOAL_PROGRESS) +
        (p_score * settings.WEIGHT_PROTECTION_BUFFER)
    )
    total_score = round(max(0.0, min(100.0, total_score)), 1)
    
    if total_score >= 80.0:
        band = "Excellent"
        summary = "Your financial health is in top shape! Disciplined cashflow, robust emergency cushion, and balanced investments."
    elif total_score >= 60.0:
        band = "Good"
        summary = "Healthy financial foundation with clear opportunities to optimize loan payoff and systematic investing."
    elif total_score >= 40.0:
        band = "Fair"
        summary = "Moderate risk exposure. Focusing on building an emergency buffer and clearing high-interest debt will quickly elevate your score."
    else:
        band = "Needs Attention"
        summary = "High financial vulnerability. Immediate corrective steps required to contain expenses and build cash reserves."
        
    return {
        "score": total_score,
        "band": band,
        "summary": summary,
        "sub_scores": [
            {"key": "savings_rate", "name": "Savings Rate", "score": round(s_score, 1), "weight": f"{int(settings.WEIGHT_SAVINGS_RATE * 100)}%", "reason": s_reason},
            {"key": "emergency_fund", "name": "Emergency Cushion", "score": round(e_score, 1), "weight": f"{int(settings.WEIGHT_EMERGENCY_FUND * 100)}%", "reason": e_reason},
            {"key": "debt_ratio", "name": "Debt Management", "score": round(d_score, 1), "weight": f"{int(settings.WEIGHT_DEBT_TO_INCOME * 100)}%", "reason": d_reason},
            {"key": "diversification", "name": "Diversification", "score": round(div_score, 1), "weight": f"{int(settings.WEIGHT_DIVERSIFICATION * 100)}%", "reason": div_reason},
            {"key": "goal_progress", "name": "Goal Progress", "score": round(g_score, 1), "weight": f"{int(settings.WEIGHT_GOAL_PROGRESS * 100)}%", "reason": g_reason},
            {"key": "protection", "name": "Protection & Insurance", "score": round(p_score, 1), "weight": f"{int(settings.WEIGHT_PROTECTION_BUFFER * 100)}%", "reason": p_reason}
        ]
    }

def generate_monthly_action_plan(
    cashflow: Dict[str, Any],
    emergency: Dict[str, Any],
    debt: Dict[str, Any],
    goals: Dict[str, Any],
    retirement: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generates a prioritised, dated checklist for the next 3 months.
    Strict priority hierarchy:
    1. Emergency Fund (Liquidity first)
    2. High-Interest Debt (Avalanche payoff)
    3. Insurance & Protection Buffer
    4. Life Goals (SIPs for medium/short-term milestones)
    5. Long-term Retirement Compounding
    
    Timing is strictly grounded in cashflow (e.g. Day 1-5 post-salary).
    Never includes market predictions or buy/sell recommendations for specific days.
    """
    actions = []
    
    # Priority 1: Emergency Fund
    if emergency["gap"] > 0:
        actions.append({
            "step": 1,
            "priority": "Highest",
            "category": "Emergency Cushion",
            "action": f"Transfer ₹{emergency['recommended_monthly_allocation']:,.0f} into Liquid / Sweep-in Account",
            "timing": "Day 1-3 after salary credit",
            "reason": f"Close the ₹{emergency['gap']:,.0f} emergency cushion gap to reach {emergency['target_months']} months of runway.",
            "completed": False
        })
    else:
        actions.append({
            "step": 1,
            "priority": "Maintenance",
            "category": "Emergency Cushion",
            "action": "Maintain emergency buffer auto-sweep in bank",
            "timing": "Ongoing quarterly check",
            "reason": f"Your emergency fund is fully funded with {emergency['months_covered']:.1f} months of expenses.",
            "completed": True
        })
        
    # Priority 2: High-Interest Debt Payoff
    if debt.get("has_loans") and debt.get("pay_this_first"):
        first_loan = debt["pay_this_first"]
        extra = debt.get("extra_prepay_simulated", 2000.0)
        actions.append({
            "step": 2,
            "priority": "High",
            "category": "Debt Payoff",
            "action": f"Prepay extra ₹{extra:,.0f}/month towards {first_loan['loan_name']}",
            "timing": "Day 5 of the month (post-salary)",
            "reason": f"{first_loan['loan_name']} carries the highest interest at {first_loan['interest_rate']}%. Clearing it saves up to ₹{debt['avalanche_plan']['interest_saved_vs_baseline']:,.0f} in interest drag.",
            "completed": False
        })
        
    # Priority 3: Insurance Buffer
    actions.append({
        "step": 3,
        "priority": "High",
        "category": "Risk Protection",
        "action": "Verify Pure Term Life Insurance & Comprehensive Family Health Cover",
        "timing": "Month 1 (Immediate)",
        "reason": "Protect your family's financial plan with 10-15x annual income term cover and ₹10L+ base health cover with super top-up.",
        "completed": False
    })
    
    # Priority 4: Goal SIPs
    active_goals = [g for g in goals.get("goals", []) if g.get("required_monthly_sip", 0) > 0]
    if active_goals:
        top_goal = active_goals[0]
        actions.append({
            "step": 4,
            "priority": "Medium",
            "category": "Goal Achievement",
            "action": f"Set up auto-debit SIP of ₹{top_goal['required_monthly_sip']:,.0f}/month for '{top_goal['name']}'",
            "timing": "Day 7 of the month",
            "reason": f"Target milestone: ₹{top_goal['target_amount']:,.0f} by {top_goal['target_date']}. Automated SIP enforces savings discipline.",
            "completed": False
        })
        
    # Priority 5: Retirement Compounding
    if retirement.get("additional_monthly_sip_needed", 0) > 0:
        retire_sip = min(retirement["additional_monthly_sip_needed"], max(1000.0, cashflow["savings_capacity"] * 0.25))
        actions.append({
            "step": 5,
            "priority": "Long-Term",
            "category": "Retirement Security",
            "action": f"Initiate ₹{retire_sip:,.0f}/month SIP in Index Funds / PPF / NPS",
            "timing": "Day 10 of the month",
            "reason": f"Compounding over {retirement['years_to_retirement']} years to bridge the ₹{retirement['corpus_gap']:,.0f} retirement corpus gap.",
            "completed": False
        })
    else:
        actions.append({
            "step": 5,
            "priority": "Long-Term",
            "category": "Retirement Security",
            "action": "Maintain existing EPF/NPS/SIP contributions",
            "timing": "Monthly automated",
            "reason": "Your current pace is projected to satisfy your retirement target corpus comfortably.",
            "completed": True
        })
        
    return actions

def simulate_whatif(
    base_profile: Dict[str, Any],
    extra_monthly_savings: float = 0.0,
    return_adjustment: float = 0.0,
    inflation_adjustment: float = 0.0,
    retirement_age_override: Optional[int] = None,
    loan_prepayment_monthly: float = 0.0
) -> Dict[str, Any]:
    """
    Live What-If Simulation Engine:
    Recalculates health score, retirement gap, debt-free date, and goal feasibility
    given modified parameters. Returns a before-and-after comparison.
    """
    # 1. Base calculations
    monthly_income = base_profile.get("monthly_income", 50000.0)
    fixed_expenses = base_profile.get("fixed_expenses", {})
    variable_expenses = base_profile.get("variable_expenses", {})
    loans = base_profile.get("loans", [])
    savings = base_profile.get("savings", 0.0)
    dependents = base_profile.get("dependents", 0)
    goals = base_profile.get("goals", [])
    age = base_profile.get("age", 28)
    retire_age = retirement_age_override if retirement_age_override else base_profile.get("retirement_age", 60)
    investments = base_profile.get("investments", [])
    risk = base_profile.get("risk_appetite", "Medium")
    
    # Baseline
    base_cf = calculate_cashflow(monthly_income, fixed_expenses, variable_expenses, loans)
    base_em = calculate_emergency_fund(base_cf["total_fixed_expenses"], base_cf["total_variable_expenses"], dependents, savings, base_cf["savings_capacity"])
    base_debt = calculate_debt_analysis(loans, monthly_income, base_cf["savings_capacity"])
    base_goals = calculate_goals(goals, base_cf["savings_capacity"])
    
    total_retire_savings = sum(float(i.get("current_value", 0.0)) for i in investments if i.get("type") in ["ppf_nps", "mutual_fund", "stocks", "epf", "fd"])
    total_retire_sip = sum(float(i.get("monthly_contribution", 0.0)) for i in investments if i.get("type") in ["ppf_nps", "mutual_fund", "stocks", "epf"])
    
    base_retire = calculate_retirement(age, base_profile.get("retirement_age", 60), base_cf["total_expenses"], total_retire_savings, total_retire_sip)
    base_health = calculate_financial_health_score(
        base_cf["savings_rate"],
        base_em["months_covered"],
        base_debt["dti_ratio"],
        len(investments),
        base_goals["goals_on_track_ratio"],
        has_insurance_or_dependents_covered=True if dependents == 0 or any("insur" in str(k).lower() for k in fixed_expenses.keys()) else False
    )
    
    # Simulated scenario
    sim_income = monthly_income + extra_monthly_savings
    sim_inflation = max(2.0, min(15.0, settings.INFLATION_RATE_DEFAULT + inflation_adjustment))
    sim_equity_return = max(4.0, min(20.0, settings.EQUITY_INDEX_RETURN + return_adjustment))
    
    sim_cf = calculate_cashflow(sim_income, fixed_expenses, variable_expenses, loans)
    sim_em = calculate_emergency_fund(sim_cf["total_fixed_expenses"], sim_cf["total_variable_expenses"], dependents, savings, sim_cf["savings_capacity"])
    
    # Prepayment simulation
    sim_debt = calculate_debt_analysis(loans, sim_income, sim_cf["savings_capacity"] + loan_prepayment_monthly)
    sim_goals = calculate_goals(goals, sim_cf["savings_capacity"], general_inflation=sim_inflation, expected_return=sim_equity_return)
    sim_retire = calculate_retirement(
        age,
        retire_age,
        sim_cf["total_expenses"],
        total_retire_savings,
        total_retire_sip + (extra_monthly_savings * 0.5), # assume 50% of extra goes to long-term
        inflation_rate=sim_inflation,
        pre_retirement_return=sim_equity_return,
        safe_withdrawal_rate=settings.SAFE_WITHDRAWAL_RATE
    )
    
    sim_health = calculate_financial_health_score(
        sim_cf["savings_rate"],
        sim_em["months_covered"],
        sim_debt["dti_ratio"],
        len(investments),
        sim_goals["goals_on_track_ratio"],
        has_insurance_or_dependents_covered=True if dependents == 0 or any("insur" in str(k).lower() for k in fixed_expenses.keys()) else False
    )
    
    return {
        "inputs_adjusted": {
            "extra_monthly_savings": extra_monthly_savings,
            "return_adjustment": return_adjustment,
            "effective_return": sim_equity_return,
            "inflation_adjustment": inflation_adjustment,
            "effective_inflation": sim_inflation,
            "retirement_age": retire_age,
            "loan_prepayment_monthly": loan_prepayment_monthly
        },
        "comparison": {
            "health_score": {
                "before": base_health["score"],
                "after": sim_health["score"],
                "delta": round(sim_health["score"] - base_health["score"], 1)
            },
            "savings_capacity": {
                "before": base_cf["savings_capacity"],
                "after": sim_cf["savings_capacity"],
                "delta": round(sim_cf["savings_capacity"] - base_cf["savings_capacity"], 2)
            },
            "retirement_corpus_gap": {
                "before": base_retire["corpus_gap"],
                "after": sim_retire["corpus_gap"],
                "delta": round(sim_retire["corpus_gap"] - base_retire["corpus_gap"], 2)
            },
            "retirement_extra_sip_needed": {
                "before": base_retire["additional_monthly_sip_needed"],
                "after": sim_retire["additional_monthly_sip_needed"],
                "delta": round(sim_retire["additional_monthly_sip_needed"] - base_retire["additional_monthly_sip_needed"], 2)
            },
            "debt_months_to_free": {
                "before": base_debt["avalanche_plan"].get("months_to_debt_free", 0) if base_debt.get("has_loans") else 0,
                "after": sim_debt["avalanche_plan"].get("months_to_debt_free", 0) if sim_debt.get("has_loans") else 0,
                "delta": (sim_debt["avalanche_plan"].get("months_to_debt_free", 0) - base_debt["avalanche_plan"].get("months_to_debt_free", 0)) if base_debt.get("has_loans") else 0
            },
            "goals_on_track_ratio": {
                "before": base_goals["goals_on_track_ratio"],
                "after": sim_goals["goals_on_track_ratio"],
                "delta": round(sim_goals["goals_on_track_ratio"] - base_goals["goals_on_track_ratio"], 1)
            }
        }
    }
