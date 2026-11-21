"""
test_api.py
Comprehensive integration tests for all API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_root_health():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_auth_and_profile_flow():
    email = "investor_test@arthmitra.ai"
    password = "securePassword123"
    
    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test Investor"
    })
    assert reg_res.status_code in [200, 400] # 400 if already exists in test run
    
    # 2. Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get Profile
    prof_res = client.get("/api/v1/profile", headers=headers)
    assert prof_res.status_code == 200
    data = prof_res.json()
    assert "monthly_income" in data
    
    # 4. Update Profile
    update_data = {
        "age": 29,
        "retirement_age": 60,
        "risk_appetite": "High",
        "dependents": 1,
        "monthly_income": 95000.0,
        "savings": 60000.0,
        "fixed_expenses": {"rent": 22000.0, "insurance": 3000.0},
        "variable_expenses": {"groceries": 15000.0, "dining": 6000.0},
        "investments": [{"name": "Index SIP", "type": "mutual_fund", "current_value": 50000.0, "monthly_contribution": 5000.0}],
        "loans": [{"name": "Car Loan", "type": "vehicle", "outstanding_amount": 150000.0, "interest_rate": 9.0, "emi": 5000.0, "remaining_tenure": 30}],
        "goals": [{"name": "Goa Trip", "category": "travel", "target_amount": 50000.0, "current_saved": 10000.0, "target_date": "2027-10", "priority": "Medium"}]
    }
    put_res = client.put("/api/v1/profile", json=update_data, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["age"] == 29
    
    # 5. Full Analysis
    ana_res = client.get("/api/v1/analysis/full", headers=headers)
    assert ana_res.status_code == 200
    analysis = ana_res.json()
    assert "health_score" in analysis
    assert "cashflow" in analysis
    assert "debt" in analysis
    assert "emergency" in analysis
    assert "goals" in analysis
    assert "allocation" in analysis
    assert "retirement" in analysis
    assert "action_plan" in analysis
    assert analysis["health_score"]["score"] > 0
    assert len(analysis["action_plan"]) >= 3
    
    # 6. What-if Analysis
    whatif_res = client.post("/api/v1/analysis/whatif", json={
        "extra_monthly_savings": 5000.0,
        "return_adjustment": 1.0,
        "inflation_adjustment": -0.5,
        "retirement_age_override": 62,
        "loan_prepayment_monthly": 2000.0
    }, headers=headers)
    assert whatif_res.status_code == 200
    whatif_data = whatif_res.json()
    assert "comparison" in whatif_data
    assert "health_score" in whatif_data["comparison"]

    # 7. Personas list and load
    personas_res = client.get("/api/v1/personas")
    assert personas_res.status_code == 200
    assert len(personas_res.json()) == 3
    
    load_res = client.post("/api/v1/personas/student/load", headers=headers)
    assert load_res.status_code == 200
    assert load_res.json()["profile"]["age"] == 21

    # 8. Chat questions (English, Hindi, Tamil)
    # Why is my score X?
    chat1 = client.post("/api/v1/chat", json={"message": "Why is my health score what it is?", "language": "en"}, headers=headers)
    assert chat1.status_code == 200
    assert "Score" in chat1.json()["reply"]

    # Refuse stock tip
    chat_stock = client.post("/api/v1/chat", json={"message": "Which stock should I buy for 50% profit next month?", "language": "en"}, headers=headers)
    assert chat_stock.status_code == 200
    assert "Index Funds" in chat_stock.json()["reply"] or "SEBI" in chat_stock.json()["reply"] or "stock tips" in chat_stock.json()["reply"]

    # Hindi chat
    chat_hi = client.post("/api/v1/chat", json={"message": "क्या मुझे लोन पहले चुकाना चाहिए?", "language": "hi"}, headers=headers)
    assert chat_hi.status_code == 200
    assert chat_hi.json()["language"] == "hi"

    # Tamil chat
    chat_ta = client.post("/api/v1/chat", json={"message": "நான் பைக்கிற்கு கடன் வாங்கலாமா?", "language": "ta"}, headers=headers)
    assert chat_ta.status_code == 200
    assert chat_ta.json()["language"] == "ta"

    # 9. Download Reports (Markdown & PDF)
    rep_md = client.get("/api/v1/report/download?format=md", headers=headers)
    assert rep_md.status_code == 200
    assert "ArthMitra" in rep_md.text

    rep_pdf = client.get("/api/v1/report/download?format=pdf", headers=headers)
    assert rep_pdf.status_code == 200
    assert rep_pdf.headers["content-type"] == "application/pdf"
    assert len(rep_pdf.content) > 1000 # Valid non-empty PDF bytes
