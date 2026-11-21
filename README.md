
# ArthMitra — AI Personal Finance Coach for India
> **Arthaton Hackathon Project** | Theme: *AI for Finance*

ArthMitra is an AI personal finance coach designed for Indian first-time investors, young professionals, and families. It diagnoses your complete financial health (income, fixed/variable expenses, loans, savings, investments, dependents, and life goals) and provides a personalized, transparent, and mathematically grounded action plan.

---

## 🏛️ Architecture Overview

```
                                  ARTHMITRA ARCHITECTURE
                                  
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                           FRONTEND (React + Vite + Tailwind)                    │
  │  - Health Score Gauge (0-100)           - Debt Avalanche vs Snowball Matrix     │
  │  - Savings & Expense Breakdown Chart    - Goals Feasibility & Suggested Fixes   │
  │  - Asset Allocation Pie & Rationale     - Interactive What-If Sliders           │
  │  - 3-Month Prioritized Action Plan      - Grounded AI Chat (English/Hindi/Tamil)│
  │  - One-Click Persona Switcher           - PDF & Markdown Plan Export            │
  └──────────────────────────────────────┬──────────────────────────────────────────┘
                                         │ REST API / JWT
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                            BACKEND (FastAPI + Python 3.11)                      │
  │                                                                                 │
  │  [API Endpoints]        [Multi-Agent Orchestrator]        [Knowledge Base]      │
  │   /auth (JWT)            ├── FinancialAgent               ├── SIP / Index Funds │
  │   /profile               ├── DebtAgent                    ├── PPF / NPS / EPF   │
  │   /analysis/full         ├── GoalAgent                    ├── Debt FDs / Gold   │
  │   /analysis/whatif       ├── InvestmentAgent              ├── Emergency Fund    │
  │   /chat                  ├── CoachAgent (Grounded)        └── Tax Basics (80C)  │
  │   /report/download       └── ReportAgent (PDF/MD)                               │
  │                                      │                                          │
  │                                      ▼                                          │
  │                     ┌───────────────────────────────────┐                       │
  │                     │      finance_engine.py            │                       │
  │                     │   (100% Pure Math Functions)      │                       │
  │                     │  - Cashflow & Savings Rate        │                       │
  │                     │  - Emergency Runway (6/9 months)  │                       │
  │                     │  - Debt Avalanche vs Snowball     │                       │
  │                     │  - Inflation-Adjusted Goals       │                       │
  │                     │  - Asset Allocation Rules         │                       │
  │                     │  - Safe Withdrawal Retirement     │                       │
  │                     │  - Financial Health Score (0-100) │                       │
  │                     └───────────────────────────────────┘                       │
  │                                      │                                          │
  │                                      ▼                                          │
  │                          SQLite Database (Local)                                │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Instructions

### 1. Backend Setup & Run

Open terminal in the project root:

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run backend server
python -m uvicorn main:app --port 8000 --app-dir backend --reload
```

The backend API will start at: `http://127.0.0.1:8000`  
Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup & Run

In a second terminal:

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

The frontend application will open at: `http://localhost:5173`

---

## 🧪 Running Automated Tests

ArthMitra includes a comprehensive test suite covering math calculations, edge cases, API endpoints, and end-to-end persona flows.

```bash
# Run unit tests for finance_engine.py
python -m pytest backend/tests/test_finance_engine.py -v

# Run API integration tests
python -m pytest backend/tests/test_api.py -v

# Run full end-to-end verification covering all 3 personas
python backend/tests/verify_personas_e2e.py
```

---

## 🌟 Key Features

1. **Financial Health Score (0-100)**: Evaluates savings rate (20%), emergency cushion (25%), debt-to-income (20%), asset diversification (15%), goal progress (10%), and insurance/protection buffer (10%). Includes visual radial gauge and "Why this advice?" expanders.
2. **Savings & Expense Analysis**: Net savings capacity, savings rate benchmarking, visual expense breakdown, and automated top-3 discretionary spending trims with monthly savings potential.
3. **Debt Avalanche vs Snowball**: Debt-to-income (DTI) ratio, loans ranked by interest rate, comparison of total interest saved, and a clear "Pay this first" recommendation.
4. **Inflation-Adjusted Goals Engine**: Mathematical future value adjustment (6% general inflation, 8.5% education inflation), required monthly SIP calculation, feasibility status (*On Track / At Risk / Unrealistic*), and actionable fixes.
5. **Rule-Based Asset Allocation**: Transparent category-level split (Equity Index, Retirement PPF/NPS, High-Grade Debt, Liquid Emergency, Gold Hedge) derived from age and risk appetite. Real estate is explicitly flagged as illiquid and capital-heavy.
6. **3-Month Action Plan**: Strictly ordered checklist: (1) Emergency Fund → (2) High-Interest Debt → (3) Protection Buffer → (4) Milestone Goals → (5) Retirement. Timed exclusively to monthly post-salary cashflow dates (Day 1-5).
7. **Retirement Planning**: Safe withdrawal rate (4%), inflation-adjusted post-retirement expenses, target corpus calculation, projected trajectory, and required extra monthly SIP.
8. **Interactive What-If Simulation**: 5 live sliders (extra savings, loan prepayment, retirement age, market return sensitivity, inflation adjustment) with real-time before-vs-after delta cards and charts.
9. **Multi-Lingual Grounded AI Coach**: Supports English, Hindi (हिन्दी), and Tamil (தமிழ்). Fully grounded in local financial knowledge and deterministic metrics. Strictly refuses individual stock tips or market predictions.
10. **One-Click Sample Personas**:
   - **Student (Aarav Sharma, 21)**: ₹22k/mo stipend, ₹0 debt, high risk, small index SIP, laptop goal.
   - **Salaried Professional (Priya Patel, 28)**: ₹88k/mo income, 42% credit card debt, education loan, emergency fund gap.
   - **Family with Home Loan (Rajesh & Meena Verma, 38)**: ₹1.75L/mo income, 3 dependents, home loan, child education & retirement goals.
11. **One-Click Report Export**: Download complete, formatted PDF and Markdown financial plans.

---

## 🔒 Privacy & Compliance Disclaimers

- **Educational Guidance Only**: This application provides educational financial diagnostics and does not constitute registered investment advice under SEBI (Investment Advisers) Regulations, 2013.
- **Local Data Privacy**: All user profile data, loans, and assets remain on the user's local device/instance and are not transmitted to third parties.

---

## 👥 Hackathon Team & Project Info
- **Event**: Arthaton 2026
- **Theme**: AI for Finance
- **Project Name**: ArthMitra (अर्थमित्र)
