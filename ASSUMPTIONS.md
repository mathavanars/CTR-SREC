# ArthMitra — Architectural & Financial Assumptions

All assumptions recorded transparently as per hackathon instructions. Each assumption is tailored for Indian retail first-time investors.

1. **Default Inflation Rate (6.0% p.a.)**: Aligned with the Reserve Bank of India (RBI) consumer price inflation target upper tolerance band (4% ± 2%).
2. **Higher Education & Child Goal Inflation Rate (8.5% p.a.)**: Education and healthcare costs in India historically inflate at 8-10%, higher than headline CPI.
3. **Long-Term Equity Index CAGR (12.0% p.a.)**: Conservative benchmark based on rolling 15-20 year historical CAGR of Nifty 50 and BSE Sensex.
4. **Fixed Deposit & High-Quality Debt Return (7.0% p.a.)**: Reflects average pre-tax term deposit yields across scheduled commercial banks in India (SBI, HDFC, ICICI).
5. **Liquid Fund & Overnight Savings Rate (4.5% p.a.)**: Reflects typical yields on overnight mutual funds and high-yield savings accounts without market volatility.
6. **Gold Long-Term Return (8.0% p.a.)**: Based on historical rupee-denominated gold appreciation reflecting sovereign gold bond yields and rupee depreciation hedge.
7. **Retirement Compounding (PPF / NPS / EPF Composite: 8.5% p.a.)**: Hybrid blend reflecting 7.1% guaranteed PPF/EPF rates plus 10-12% moderate equity allocation under NPS Tier 1.
8. **Emergency Cushion Sizing (6 months for single, 9 months with dependents or irregular income)**: Six months covers median job transition time in India; 9 months accounts for family healthcare contingencies and school tuition continuity.
9. **Emergency Essential Expenses Definition (100% Fixed + 60% Variable)**: Discretionary lifestyle spending (dining out, entertainment, shopping) can be compressed by 40% in an emergency.
10. **Debt Avalanche Method Default**: Statistically saves the maximum rupees in interest drag by tackling highest APR loans (such as 42% credit cards) first.
11. **Debt Snowball Option Included for Psychological Momentum**: Eliminating smaller balances early provides behavioural reinforcement for anxious first-time investors.
12. **Safe Withdrawal Rate in Retirement (4.0% p.a.)**: Classic Trinity Study benchmark adapted for Indian life expectancy (up to age 85, providing 25-30 years of post-retirement income).
13. **Real Estate Classified as Unsuitable for Early Wealth Creation**: Property purchases require illiquid lump sums, incur 6-8% transaction friction (stamp duty + registration), have low rental yields (2-3%), and lock early earners into heavy EMI debt traps.
14. **No Stock Tipping or Single-Fund Promotion**: Strictly complies with SEBI (Investment Advisers) Regulations, 2013 by restricting guidance to transparent category asset allocations (Index Funds, PPF, Debt, Gold).
15. **Multi-Agent Decoupled Architecture**: All mathematics and compounding formulas live strictly in `finance_engine.py` (pure Python functions), ensuring zero LLM hallucination of financial numbers.
16. **Offline Grounded Fallback Chat Engine**: When external LLM API keys are absent, deterministic rule-based grounded logic responds in English, Hindi, and Tamil, guaranteeing 100% hackathon demo uptime.
17. **Client-Side Data Privacy**: SQLite local storage and in-browser state ensure financial privacy; user financial figures are never transmitted to third-party ad networks.
