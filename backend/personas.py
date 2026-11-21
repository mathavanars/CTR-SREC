"""
personas.py
One-click realistic sample personas for demo and judges.
"""
from typing import Dict, Any

PERSONAS: Dict[str, Dict[str, Any]] = {
    "student": {
        "id": "student",
        "name": "Aarav Sharma",
        "tagline": "21 y/o Student / Tech Intern starting early",
        "description": "Modest stipend income, zero debt, wants to buy a professional development laptop and learn investing habits.",
        "profile": {
            "age": 21,
            "retirement_age": 60,
            "risk_appetite": "High",
            "dependents": 0,
            "monthly_income": 22000.0,
            "savings": 18000.0,
            "fixed_expenses": {
                "shared_rent_wifi": 5500.0,
                "learning_subscriptions": 1200.0
            },
            "variable_expenses": {
                "food_mess": 6000.0,
                "local_commute": 1800.0,
                "entertainment_hangouts": 2000.0
            },
            "investments": [
                {
                    "name": "Nifty Index SIP",
                    "type": "mutual_fund",
                    "current_value": 8500.0,
                    "monthly_contribution": 1500.0
                }
            ],
            "loans": [],
            "goals": [
                {
                    "name": "High-Performance Developer Laptop",
                    "category": "education",
                    "target_amount": 75000.0,
                    "current_saved": 10000.0,
                    "target_date": "2027-10",
                    "priority": "High"
                },
                {
                    "name": "Post-Graduation Emergency Cushion",
                    "category": "emergency",
                    "target_amount": 120000.0,
                    "current_saved": 8000.0,
                    "target_date": "2028-06",
                    "priority": "Medium"
                }
            ]
        }
    },
    "salaried_with_loan": {
        "id": "salaried_with_loan",
        "name": "Priya Patel",
        "tagline": "28 y/o Salaried Engineer balancing loans & dreams",
        "description": "Healthy salary but burdened by an education loan and a high-interest credit card balance with an emergency fund gap.",
        "profile": {
            "age": 28,
            "retirement_age": 60,
            "risk_appetite": "Medium",
            "dependents": 0,
            "monthly_income": 88000.0,
            "savings": 45000.0,
            "fixed_expenses": {
                "house_rent": 20000.0,
                "utilities_broadband": 3500.0,
                "term_health_insurance": 2500.0,
                "gym_subscriptions": 2000.0
            },
            "variable_expenses": {
                "groceries_food": 14000.0,
                "cabs_fuel": 4500.0,
                "shopping_lifestyle": 7000.0,
                "weekend_dining": 5000.0
            },
            "investments": [
                {
                    "name": "Large & Midcap Mutual Fund",
                    "type": "mutual_fund",
                    "current_value": 145000.0,
                    "monthly_contribution": 6000.0
                },
                {
                    "name": "Public Provident Fund",
                    "type": "ppf_nps",
                    "current_value": 90000.0,
                    "monthly_contribution": 2500.0
                }
            ],
            "loans": [
                {
                    "id": "l1",
                    "name": "HDFC Credit Card Rolling Balance",
                    "type": "credit_card",
                    "outstanding_amount": 48000.0,
                    "interest_rate": 42.0,
                    "emi": 4200.0,
                    "remaining_tenure": 12
                },
                {
                    "id": "l2",
                    "name": "SBI Higher Education Loan",
                    "type": "education",
                    "outstanding_amount": 320000.0,
                    "interest_rate": 10.5,
                    "emi": 8900.0,
                    "remaining_tenure": 42
                }
            ],
            "goals": [
                {
                    "name": "Electric Vehicle (EV) Purchase",
                    "category": "vehicle",
                    "target_amount": 750000.0,
                    "current_saved": 40000.0,
                    "target_date": "2029-03",
                    "priority": "Medium"
                },
                {
                    "name": "Wedding / Relocation Corpus",
                    "category": "personal",
                    "target_amount": 500000.0,
                    "current_saved": 50000.0,
                    "target_date": "2028-11",
                    "priority": "High"
                }
            ]
        }
    },
    "family_home_loan": {
        "id": "family_home_loan",
        "name": "Rajesh & Meena Verma",
        "tagline": "38 y/o Mid-Career Professional with dependents & home loan",
        "description": "High household income with significant financial commitments: home loan EMI, school fees for 2 kids, and elderly mother care.",
        "profile": {
            "age": 38,
            "retirement_age": 60,
            "risk_appetite": "Medium",
            "dependents": 3,
            "monthly_income": 175000.0,
            "savings": 220000.0,
            "fixed_expenses": {
                "children_school_tuition": 18000.0,
                "groceries_household": 22000.0,
                "family_floater_health_insurance": 6500.0,
                "mother_medical_prescriptions": 5500.0,
                "apartment_society_maintenance": 4500.0
            },
            "variable_expenses": {
                "domestic_travel_vacations": 10000.0,
                "family_dining_entertainment": 8000.0,
                "vehicle_fuel_maintenance": 6000.0,
                "miscellaneous_shopping": 7000.0
            },
            "investments": [
                {
                    "name": "Employee Provident Fund (EPF)",
                    "type": "epf",
                    "current_value": 850000.0,
                    "monthly_contribution": 12000.0
                },
                {
                    "name": "Flexi Cap & Index Equity Funds",
                    "type": "mutual_fund",
                    "current_value": 620000.0,
                    "monthly_contribution": 15000.0
                },
                {
                    "name": "Sovereign Gold Bonds (SGB)",
                    "type": "gold",
                    "current_value": 240000.0,
                    "monthly_contribution": 0.0
                }
            ],
            "loans": [
                {
                    "id": "l1",
                    "name": "SBI MaxGain Home Loan",
                    "type": "home",
                    "outstanding_amount": 3650000.0,
                    "interest_rate": 8.65,
                    "emi": 35200.0,
                    "remaining_tenure": 164
                },
                {
                    "id": "l2",
                    "name": "ICICI Car Loan",
                    "type": "vehicle",
                    "outstanding_amount": 280000.0,
                    "interest_rate": 9.25,
                    "emi": 9800.0,
                    "remaining_tenure": 32
                }
            ],
            "goals": [
                {
                    "name": "Child 1 Engineering / Higher Ed Corpus",
                    "category": "education",
                    "target_amount": 2500000.0,
                    "current_saved": 400000.0,
                    "target_date": "2032-06",
                    "priority": "High"
                },
                {
                    "name": "Comfortable Retirement Corpus",
                    "category": "retirement",
                    "target_amount": 25000000.0,
                    "current_saved": 1400000.0,
                    "target_date": "2048-06",
                    "priority": "High"
                }
            ]
        }
    }
}
