"""
verify_personas_e2e.py
End-to-end automated verification script covering all three personas,
chat in 3 languages, what-if simulations, and report exports.
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_e2e():
    print("--- Starting ArthMitra E2E Persona Verification ---")
    
    # 1. Login/Register demo user
    reg = client.post("/api/v1/auth/register", json={
        "email": "e2e_judge@arthmitra.ai",
        "password": "judgeSecretPassword123",
        "full_name": "Arthaton Judge"
    })
    token = None
    if reg.status_code == 200:
        token = reg.json()["access_token"]
    else:
        log = client.post("/api/v1/auth/login", json={
            "email": "e2e_judge@arthmitra.ai",
            "password": "judgeSecretPassword123"
        })
        token = log.json()["access_token"]
        
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Auth Token acquired.")

    # 2. Test Persona 1: Student (Aarav)
    print("\n[Testing Persona 1: Student (Aarav Sharma)]")
    p1 = client.post("/api/v1/personas/student/load", headers=headers)
    assert p1.status_code == 200
    ana1 = client.get("/api/v1/analysis/full", headers=headers).json()
    print(f"  Health Score: {ana1['health_score']['score']} ({ana1['health_score']['band']})")
    print(f"  Savings Rate: {ana1['cashflow']['savings_rate']}% | Surplus: ₹{ana1['cashflow']['savings_capacity']}")
    print(f"  Debt Count: {len(ana1['debt'].get('loans_ranked_by_interest', []))} (Has debt: {ana1['debt']['has_loans']})")
    assert ana1['debt']['has_loans'] is False
    assert ana1['cashflow']['savings_rate'] > 0
    print("✓ Student persona verified.")

    # 3. Test Persona 2: Salaried with Loan (Priya Patel)
    print("\n[Testing Persona 2: Salaried with Loan (Priya Patel)]")
    p2 = client.post("/api/v1/personas/salaried_with_loan/load", headers=headers)
    assert p2.status_code == 200
    ana2 = client.get("/api/v1/analysis/full", headers=headers).json()
    print(f"  Health Score: {ana2['health_score']['score']} ({ana2['health_score']['band']})")
    print(f"  DTI Ratio: {ana2['debt']['dti_ratio']}% ({ana2['debt']['dti_status']})")
    print(f"  Pay This First: {ana2['debt']['pay_this_first']['loan_name']} at {ana2['debt']['pay_this_first']['interest_rate']}% interest")
    print(f"  Avalanche Interest Saved: ₹{ana2['debt']['avalanche_plan']['interest_saved_vs_baseline']:,.0f}")
    assert ana2['debt']['pay_this_first']['interest_rate'] >= 40.0 # 42% credit card
    assert ana2['emergency']['gap'] > 0
    print("✓ Salaried persona verified.")

    # 4. Test Persona 3: Family with Home Loan (Rajesh Verma)
    print("\n[Testing Persona 3: Family with Home Loan (Rajesh & Meena Verma)]")
    p3 = client.post("/api/v1/personas/family_home_loan/load", headers=headers)
    assert p3.status_code == 200
    ana3 = client.get("/api/v1/analysis/full", headers=headers).json()
    print(f"  Health Score: {ana3['health_score']['score']} ({ana3['health_score']['band']})")
    print(f"  Monthly Income: ₹{ana3['cashflow']['monthly_income']:,.0f}")
    print(f"  Retirement Target Corpus: ₹{ana3['retirement']['target_corpus']:,.0f}")
    print(f"  Retirement Gap: ₹{ana3['retirement']['corpus_gap']:,.0f}")
    print(f"  Emergency Target Months: {ana3['emergency']['target_months']} months (Dependents: 3)")
    assert ana3['emergency']['target_months'] == 9 # 9 months due to dependents
    assert ana3['retirement']['target_corpus'] > 10000000 # > 1 Cr
    print("✓ Family persona verified.")

    # 5. What-If Simulation
    print("\n[Testing What-If Simulation]")
    sim = client.post("/api/v1/analysis/whatif", json={
        "extra_monthly_savings": 10000,
        "return_adjustment": 1.5,
        "inflation_adjustment": -1.0,
        "retirement_age_override": 58,
        "loan_prepayment_monthly": 5000
    }, headers=headers).json()
    print(f"  Health Score Before: {sim['comparison']['health_score']['before']} -> After: {sim['comparison']['health_score']['after']}")
    print(f"  Retirement Gap Delta: ₹{sim['comparison']['retirement_corpus_gap']['delta']:,.0f}")
    assert "comparison" in sim
    print("✓ What-If Simulation verified.")

    # 6. Chat in English, Hindi, Tamil & Refusal of Stock Tips
    print("\n[Testing Multi-lingual AI Chat & Grounding]")
    chat_en = client.post("/api/v1/chat", json={"message": "Can I afford a bike loan?", "language": "en"}, headers=headers).json()
    print(f"  EN Chat Reply Snippet: {chat_en['reply'][:100]}...")
    assert len(chat_en['reply']) > 20

    chat_hi = client.post("/api/v1/chat", json={"message": "क्या मुझे लोन पहले चुकाना चाहिए?", "language": "hi"}, headers=headers).json()
    print(f"  HI Chat Reply Snippet: {chat_hi['reply'][:100]}...")
    assert len(chat_hi['reply']) > 20

    chat_ta = client.post("/api/v1/chat", json={"message": "அவசரகால நிதி எவ்வளவு வேண்டும்?", "language": "ta"}, headers=headers).json()
    print(f"  TA Chat Reply Snippet: {chat_ta['reply'][:100]}...")
    assert len(chat_ta['reply']) > 20

    chat_stock = client.post("/api/v1/chat", json={"message": "Which penny stock will give 100% return?", "language": "en"}, headers=headers).json()
    print(f"  Stock Tip Guardrail: {chat_stock['reply'][:100]}...")
    assert "Index Funds" in chat_stock['reply'] or "do not provide individual stock tips" in chat_stock['reply']
    print("✓ AI Chat & Guardrails verified.")

    # 7. Report Generation (PDF & Markdown)
    print("\n[Testing Report Downloads]")
    rep_pdf = client.get("/api/v1/report/download?format=pdf", headers=headers)
    assert rep_pdf.status_code == 200
    assert len(rep_pdf.content) > 1000
    print(f"  PDF Generated: {len(rep_pdf.content)} bytes")

    rep_md = client.get("/api/v1/report/download?format=md", headers=headers)
    assert rep_md.status_code == 200
    assert len(rep_md.text) > 500
    print(f"  Markdown Generated: {len(rep_md.text)} chars")
    print("✓ Reports verified.")

    print("\n=== ALL E2E PERSONAS AND FEATURES VERIFIED WITH ZERO ERRORS ===")

if __name__ == "__main__":
    run_e2e()
