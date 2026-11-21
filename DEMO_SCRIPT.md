# ArthMitra — Hackathon Demo Script & Judge Q&A

## 2-Minute Demo Script (Arthaton Pitch)
**Persona Selected:** Priya Patel (28 y/o Software Engineer, ₹88,000/mo income, HDFC Credit Card balance at 42% APR, SBI Education loan, ₹45,000 savings buffer).

### [0:00 - 0:25] The Problem & The Solution
> "Good morning, judges! In India, millions of young professionals earn healthy salaries but face financial paralysis: How much should I save? Should I prepay my education loan or start an SIP? Why is my credit card balance growing?
>
> Meet **ArthMitra** — India's first AI personal finance coach built on a 100% deterministic, explainable calculation engine. ArthMitra doesn't guess or hallucinate numbers; it diagnoses a user's entire financial life and provides a clear, actionable plan."

### [0:25 - 0:50] Instant Diagnosis & Financial Health Score
> *(Click on 'Overview & Score')*
> "With one click, we load Priya's profile. Immediately, our engine calculates her **Financial Health Score: 56/100 (Fair)**.
> Notice the 6 sub-scores: while her savings rate is decent (22.7%), her emergency cushion is dangerously low (covers only 0.9 months), and she is bleeding interest on her debt.
> Click *'Why this advice?'* on any card: every recommendation is fully transparent, explaining the exact rule and math behind it."

### [0:50 - 1:15] Mathematical Debt Avalanche & Savings Trims
> *(Navigate to 'Debt & Loans', then 'Savings & Cashflow')*
> "Under Debt Analysis, ArthMitra detects her 42% HDFC credit card debt alongside a 10.5% education loan. Instead of generic advice, our Avalanche engine recommends: **'Pay This First: HDFC Credit Card'**, demonstrating that an extra ₹2,000/mo prepayment saves ₹28,181 in pure interest drag!
> In Savings Analysis, ArthMitra pinpoints her top 3 discretionary trims (Dining, Shopping), unlocking ₹4,000/month extra without hurting her living standard."

### [1:15 - 1:40] Life Goals, Retirement & What-If Simulation
> *(Click 'What-If Simulator')*
> "Priya dreams of buying an EV car and retiring by 60. But look at our live What-If sliders:
> As Priya slides *'Extra Monthly Savings'* by +₹5,000/mo, watch the health score jump from 56 to 65, and her debt-free date accelerate by 8 months live on the chart! No static spreadsheets—live dynamic projections."

### [1:40 - 2:00] Multi-Lingual AI Chat & Zero-Hallucination Compliance
> *(Click 'AI Financial Coach', select हिन्दी or தமிழ்)*
> "Let's ask the coach in Hindi or Tamil: *'Should I prepay my loan or start a SIP?'*
> The coach consults our local knowledge base and financial engine, stating: *'Prepay the 42% card first—a guaranteed 42% expense saved beats the uncertain 12% equity market.'*
> And if someone asks for stock tips? The system strictly refuses under SEBI guidelines and redirects to broad index funds. Finally, with one click, Priya exports a complete PDF financial plan.
> ArthMitra turns financial anxiety into financial freedom!"

---

## 8 Likely Judge Questions & Sharp Answers

### Q1: "How do you guarantee that the AI doesn't hallucinate numbers or give illegal financial advice?"
**Answer:** "By architectural design, **zero mathematics is performed by the LLM**. All formulas (compound interest, future value, avalanche schedules, emergency multipliers) are pure Python functions in `finance_engine.py`. The LLM or grounded template engine only verbalizes deterministic figures retrieved directly from the engine. Furthermore, we enforce strict compliance filters: the system explicitly refuses stock tips or market predictions and recommends only category-level asset allocations."

### Q2: "How does your asset allocation logic adapt to an Indian first-time investor?"
**Answer:** "We use an age-adjusted equity rule ($100 - \text{age}$) calibrated by risk tolerance (capped at 45% for Low, 65% for Medium, 80% for High). Crucially, if an emergency fund gap exists, 30% of monthly surplus is prioritized into liquid funds first. We also incorporate a 7% Sovereign Gold allocation as a domestic currency hedge and utilize tax-advantaged sovereign debt (PPF/EPF/NPS) for retirement."

### Q3: "Why did you exclude Real Estate from monthly investment allocations?"
**Answer:** "For early and mid-career earners, real estate requires large capital outlays, high transaction friction (6-8% stamp duty and registration), has low rental yields (2-3% in urban India), and locks young professionals into rigid multi-decade EMIs. We explicitly educate users that liquid diversified portfolios must precede illiquid real estate bets."

### Q4: "How does the Emergency Fund sizing logic work?"
**Answer:** "It evaluates essential survival expenses ($100\% \text{ Fixed} + 60\% \text{ Variable}$). For single individuals with stable jobs, it targets 6 months of expenses. If the user records dependents or irregular income, the target automatically expands to 9 months, parked across instant bank savings (30%), overnight mutual funds (40%), and auto-sweep FDs (30%)."

### Q5: "What is the difference between Debt Avalanche and Debt Snowball in your engine?"
**Answer:** "Debt Avalanche orders loans by highest interest rate descending, mathematically minimizing total interest paid (saving thousands of rupees). Debt Snowball orders by smallest outstanding balance first, providing quick psychological wins. We show both, but highlight Avalanche as the financially optimal strategy."

### Q6: "How do you support multi-lingual accessibility for non-English speakers?"
**Answer:** "ArthMitra features full English, Hindi (हिन्दी), and Tamil (தமிழ்) localization across the UI and AI coach. The assistant understands regional financial concepts (e.g. PPF, chit fund risks, FD auto-sweep) and responds in natural conversational vernacular."

### Q7: "What happens if a user has zero income or negative cashflow?"
**Answer:** "Our engine includes comprehensive edge-case handling. If income is zero or expenses exceed income, it flags 'Deficit / Critical' status, suspends new investment suggestions, and directs 100% of the action plan to emergency spending cuts and debt restructuring before any goal investing."

### Q8: "How does the app handle data privacy?"
**Answer:** "All user profiles, liabilities, and financial data reside locally in an isolated SQLite database on the user's personal instance. No user data is sent to external advertising networks or commercial brokers."
