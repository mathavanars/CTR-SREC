/**
 * ArthMitra - API Client Layer with Mock Fallback & FastAPI Integration
 *
 * ============================================================================
 * EXPECTED API REQUEST & RESPONSE JSON SCHEMAS:
 * ============================================================================
 *
 * 1. POST /auth/register
 *    Request:  { "name": "Rahul Sharma", "email": "rahul@example.in", "password": "Password@123" }
 *    Response: { "token": "jwt_token_string", "user": { "id": "u1", "name": "Rahul Sharma", "email": "rahul@example.in" } }
 *
 * 2. POST /auth/login
 *    Request:  { "email": "rahul@example.in", "password": "Password@123" }
 *    Response: { "token": "jwt_token_string", "user": { "id": "u1", "name": "Rahul Sharma", "email": "rahul@example.in" } }
 *
 * 3. GET /auth/me
 *    Header:   Authorization: Bearer <token>
 *    Response: { "id": "u1", "name": "Rahul Sharma", "email": "rahul@example.in" }
 *
 * 4. GET /profile
 *    Response: {
 *      "income": { "salary": 85000, "rental": 15000, "other": 5000 },
 *      "fixedExpenses": { "rent": 25000, "utilities": 6000, "emis": 18500 },
 *      "variableExpenses": { "groceries": 12000, "dining": 5000, "travel": 4000, "shopping": 5000 },
 *      "assets": { "bankFD": 350000, "mutualFunds": 850000, "ppf": 450000, "nps": 220000, "gold": 300000, "realEstate": 3500000 },
 *      "liabilities": { "homeLoan": 2200000, "carLoan": 320000, "creditCards": 25000 },
 *      "insurance": { "lifeTermCover": 10000000, "healthCover": 1000000 },
 *      "riskAppetite": "Moderate",
 *      "dependents": 2
 *    }
 *
 * 5. PUT /profile
 *    Request:  (Partial or full profile JSON object as above)
 *    Response: { "status": "success", "profile": { ... } }
 *
 * 6. GET /dashboard/summary
 *    Response: {
 *      "netWorth": 3175000,
 *      "monthlyIncome": 105000,
 *      "monthlyExpenses": 75500,
 *      "savingsRate": 28.1,
 *      "healthScore": 74,
 *      "healthFactors": {
 *        "savingsRate": { "score": 80, "status": "Good (>25%)" },
 *        "emergencyCushion": { "score": 75, "status": "4.5 / 6 months" },
 *        "debtToIncome": { "score": 70, "status": "17.6% (Healthy < 35%)" },
 *        "insuranceCoverage": { "score": 72, "status": "Adequate" }
 *      },
 *      "emergencyFund": { "current": 340000, "target": 453000, "monthsCovered": 4.5, "targetMonths": 6 },
 *      "monthlyTrends": {
 *        "months": ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"],
 *        "income": [85000, 85000, 90000, 90000, 95000, 95000, 110000, 100000, 100000, 105000, 105000, 105000],
 *        "expense": [60000, 62000, 58000, 64000, 67000, 61000, 82000, 66000, 64000, 63000, 62000, 75500]
 *      },
 *      "wealthGrowth": {
 *        "labels": ["2020", "2021", "2022", "2023", "2024", "2025"],
 *        "values": [350000, 720000, 1250000, 1890000, 2600000, 3175000]
 *      },
 *      "topActions": [
 *        { "id": "act-1", "title": "Start ₹5,000 ELSS SIP", "desc": "Save up to ₹15,600 in Section 80C tax deductions before March 31.", "impact": "High Impact", "impactType": "success", "action": "investments" },
 *        { "id": "act-2", "title": "Top Up Emergency Fund", "desc": "Add ₹1.1 Lakh to reach your recommended 6-month safety buffer.", "impact": "Medium Impact", "impactType": "warning", "action": "goals" },
 *        { "id": "act-3", "title": "Accelerate Car Loan Payoff", "desc": "Paying ₹2,000 extra monthly saves ₹18,400 in interest and finishes 7 months early.", "impact": "High Impact", "impactType": "success", "action": "debts" }
 *      ]
 *    }
 *
 * 7. GET /goals
 *    Response: [
 *      { "id": "g-1", "name": "Emergency Cushion", "category": "Emergency", "targetAmount": 450000, "currentSavings": 340000, "targetDate": "2025-12-31", "priority": "High" },
 *      { "id": "g-2", "name": "House Down Payment", "category": "House", "targetAmount": 1500000, "currentSavings": 650000, "targetDate": "2027-06-30", "priority": "High" }
 *    ]
 *
 * 8. POST /goals
 *    Request:  { "name": "New Car", "category": "Vehicle", "targetAmount": 800000, "currentSavings": 150000, "targetDate": "2026-12-31", "priority": "Medium" }
 *    Response: { "id": "g-3", ... }
 *
 * 9. PUT /goals/:id & DELETE /goals/:id
 *
 * 10. GET /debts
 *     Response: {
 *       "totalDebt": 2545000,
 *       "totalMonthlyEMI": 33500,
 *       "debtToIncomeRatio": 31.9,
 *       "debts": [
 *         { "id": "d-1", "name": "SBI Home Loan", "principal": 2200000, "interestRate": 8.5, "emi": 21500, "tenureMonthsLeft": 180, "totalInterest": 1670000 },
 *         { "id": "d-2", "name": "HDFC Car Loan", "principal": 320000, "interestRate": 9.2, "emi": 9800, "tenureMonthsLeft": 38, "totalInterest": 52400 },
 *         { "id": "d-3", "name": "Credit Card Outstanding", "principal": 25000, "interestRate": 42.0, "emi": 2200, "tenureMonthsLeft": 12, "totalInterest": 6200 }
 *       ]
 *     }
 *
 * 11. POST /debts/simulate
 *     Request:  { "extraPrepayment": 5000, "strategy": "avalanche" }
 *     Response: { "totalInterestSaved": 284000, "monthsSaved": 34, "originalTenure": 180, "newTenure": 146 }
 *
 * 12. GET /investments/recommendations
 *     Response: {
 *       "riskAppetite": "Moderate",
 *       "allocations": [
 *         { "instrument": "Large & Mid Cap Index Funds", "category": "Equity", "percentage": 50, "expectedReturn": "12.0% - 14.0%", "risk": "High", "rationale": "Compounding engine to beat inflation over a 7+ year horizon.", "whyForYou": "Aligned with your 15-year wealth creation goals and moderate risk tolerance." },
 *         { "instrument": "Public Provident Fund (PPF)", "category": "Fixed Income", "percentage": 20, "expectedReturn": "7.1% Tax-Free", "risk": "Low", "rationale": "Sovereign guaranteed EEE tax-exempt fixed wealth foundation.", "whyForYou": "Secures capital for child education with zero credit risk." },
 *         { "instrument": "Sovereign Gold Bonds (SGB) / Gold ETF", "category": "Gold", "percentage": 10, "expectedReturn": "9.5% - 11.0%", "risk": "Moderate", "rationale": "Hedge against rupee depreciation and geopolitical uncertainty.", "whyForYou": "Maintains an all-weather portfolio cushion." },
 *         { "instrument": "National Pension System (NPS)", "category": "Retirement", "percentage": 10, "expectedReturn": "10.0% - 11.5%", "risk": "Moderate", "rationale": "Additional ₹50,000 tax deduction under 80CCD(1B) plus annuity safety.", "whyForYou": "Optimizes high tax bracket bracket savings for retirement." },
 *         { "instrument": "High Yield Bank Fixed Deposits / Arbitrage", "category": "Emergency / Debt", "percentage": 10, "expectedReturn": "7.0% - 7.5%", "risk": "Low", "rationale": "Instant liquidity and emergency stability.", "whyForYou": "Readily accessible without market drawdown risk." }
 *       ]
 *     }
 *
 * 13. POST /chat/message
 *     Request:  { "message": "Should I prepay my home loan or invest in an index fund SIP?" }
 *     Response: { "reply": "In the Indian context, comparing an 8.5% home loan prepayment vs a 12% equity SIP depends on tax deductions and risk tolerance..." }
 *
 * 14. GET /reports & POST /reports/generate
 * ============================================================================
 */

import { store } from './store.js';

// Configuration
export const BASE_URL = 'http://localhost:8000/api/v1';
export const USE_MOCK = true; // Set to false to connect directly to FastAPI backend

// Simulated latency in mock mode (ms)
const MOCK_LATENCY = 350;

/**
 * In-Memory & LocalStorage Mock Database for Indian Context
 */
const STORAGE_KEY_MOCK_DB = 'arthmitra_mock_database';

function getMockDB() {
  const stored = localStorage.getItem(STORAGE_KEY_MOCK_DB);
  if (stored) {
    try { return JSON.parse(stored); } catch (e) { /* fallback */ }
  }

  const initialDB = {
    user: {
      id: 'u-101',
      name: 'Rahul Sharma',
      email: 'rahul.sharma@example.in',
      phone: '+91 98765 43210'
    },
    profile: {
      income: { salary: 85000, rental: 15000, other: 5000 },
      fixedExpenses: { rent: 25000, utilities: 6000, emis: 18500 },
      variableExpenses: { groceries: 12000, dining: 5000, travel: 4000, shopping: 5000 },
      assets: { bankFD: 350000, mutualFunds: 850000, ppf: 450000, nps: 220000, gold: 300000, realEstate: 3500000 },
      liabilities: { homeLoan: 2200000, carLoan: 320000, creditCards: 25000 },
      insurance: { lifeTermCover: 10000000, healthCover: 1000000 },
      riskAppetite: 'Moderate',
      dependents: 2
    },
    goals: [
      { id: 'g-1', name: 'Emergency Cushion (6 Months)', category: 'Emergency', targetAmount: 450000, currentSavings: 340000, targetDate: '2025-12-31', priority: 'High' },
      { id: 'g-2', name: 'Apartment Down Payment', category: 'House', targetAmount: 1500000, currentSavings: 650000, targetDate: '2027-06-30', priority: 'High' },
      { id: 'g-3', name: 'Child Higher Education Fund', category: 'Education', targetAmount: 2500000, currentSavings: 420000, targetDate: '2032-05-15', priority: 'Medium' },
      { id: 'g-4', name: 'New Electric Car (EV)', category: 'Vehicle', targetAmount: 850000, currentSavings: 380000, targetDate: '2026-03-31', priority: 'Low' }
    ],
    debts: [
      { id: 'd-1', name: 'SBI Home Loan (PMAY)', principal: 2200000, interestRate: 8.5, emi: 21500, tenureMonthsLeft: 168, totalInterest: 1420000 },
      { id: 'd-2', name: 'HDFC Car Loan', principal: 320000, interestRate: 9.2, emi: 9800, tenureMonthsLeft: 36, totalInterest: 48200 },
      { id: 'd-3', name: 'Axis Bank Credit Card', principal: 25000, interestRate: 42.0, emi: 2200, tenureMonthsLeft: 12, totalInterest: 6100 }
    ],
    chatHistory: [
      {
        id: 'c-1',
        sender: 'assistant',
        text: 'Namaste Rahul! I am ArthMitra, your personal AI Financial Planning Assistant. How can I help optimize your investments, tax planning, or loan strategies today?',
        timestamp: new Date(Date.now() - 3600000).toISOString()
      }
    ],
    reports: [
      { id: 'rep-1', title: 'Q3 Financial Health Diagnostic', date: '2025-01-15', type: 'Health Check', score: 74, status: 'Generated' },
      { id: 'rep-2', title: 'FY 2024-25 Tax Optimization Audit', date: '2024-12-20', type: 'Tax Planning', score: 81, status: 'Generated' },
      { id: 'rep-3', title: 'Annual Net Worth Growth Statement', date: '2024-10-05', type: 'Net Worth', score: 70, status: 'Generated' }
    ]
  };

  localStorage.setItem(STORAGE_KEY_MOCK_DB, JSON.stringify(initialDB));
  return initialDB;
}

function saveMockDB(db) {
  localStorage.setItem(STORAGE_KEY_MOCK_DB, JSON.stringify(db));
}

/**
 * Handle simulated Mock Mode requests
 */
async function handleMockRequest(endpoint, options = {}) {
  await new Promise(resolve => setTimeout(resolve, MOCK_LATENCY));
  const method = (options.method || 'GET').toUpperCase();
  const db = getMockDB();
  const body = options.body ? JSON.parse(options.body) : {};

  // Auth endpoints
  if (endpoint === '/auth/login' || endpoint === '/auth/register') {
    const user = {
      id: db.user.id,
      name: body.name || db.user.name,
      email: body.email || db.user.email
    };
    return {
      token: 'mock_jwt_token_' + Math.random().toString(36).substring(2),
      user
    };
  }

  if (endpoint === '/auth/me') {
    return db.user;
  }

  // Profile endpoints
  if (endpoint === '/profile') {
    if (method === 'PUT') {
      db.profile = { ...db.profile, ...body };
      saveMockDB(db);
      return { status: 'success', profile: db.profile };
    }
    return db.profile;
  }

  // Dashboard summary
  if (endpoint === '/dashboard/summary') {
    const totalIncome = Object.values(db.profile.income).reduce((a, b) => a + b, 0);
    const totalExpenses = Object.values(db.profile.fixedExpenses).reduce((a, b) => a + b, 0) +
                          Object.values(db.profile.variableExpenses).reduce((a, b) => a + b, 0);
    const netSavings = totalIncome - totalExpenses;
    const savingsRate = totalIncome > 0 ? ((netSavings / totalIncome) * 100).toFixed(1) : '0';

    const totalAssets = Object.values(db.profile.assets).reduce((a, b) => a + b, 0);
    const totalLiabilities = Object.values(db.profile.liabilities).reduce((a, b) => a + b, 0);
    const netWorth = totalAssets - totalLiabilities;

    const emergencyTarget = totalExpenses * 6;
    const emergencyCurrent = db.profile.assets.bankFD || 340000;
    const monthsCovered = totalExpenses > 0 ? (emergencyCurrent / totalExpenses).toFixed(1) : 0;

    return {
      netWorth,
      monthlyIncome: totalIncome,
      monthlyExpenses: totalExpenses,
      savingsRate: parseFloat(savingsRate),
      healthScore: 74,
      healthFactors: {
        savingsRate: { score: 80, status: `${savingsRate}% (>25% target)` },
        emergencyCushion: { score: 75, status: `${monthsCovered} of 6 months target` },
        debtToIncome: { score: 72, status: '23.8% (Healthy < 35%)' },
        insuranceCoverage: { score: 70, status: 'Adequate Term Cover (₹1 Cr)' }
      },
      emergencyFund: {
        current: emergencyCurrent,
        target: emergencyTarget,
        monthsCovered: parseFloat(monthsCovered),
        targetMonths: 6
      },
      monthlyTrends: {
        months: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
        income: [85000, 85000, 90000, 90000, 95000, 95000, 110000, 100000, 100000, 105000, 105000, 105000],
        expense: [60000, 62000, 58000, 64000, 67000, 61000, 82000, 66000, 64000, 63000, 62000, totalExpenses]
      },
      wealthGrowth: {
        labels: ['2020', '2021', '2022', '2023', '2024', '2025'],
        values: [350000, 720000, 1250000, 1890000, 2600000, netWorth]
      },
      topActions: [
        {
          id: 'act-1',
          title: 'Start ₹5,000 ELSS / PPF SIP',
          desc: 'Save up to ₹15,600 in Section 80C income tax deductions before financial year end.',
          impact: 'High Impact',
          impactType: 'success',
          action: '#investments'
        },
        {
          id: 'act-2',
          title: 'Emergency Buffer Top-Up',
          desc: `You need ₹${(emergencyTarget - emergencyCurrent).toLocaleString('en-IN')} more to secure a full 6-month safety net.`,
          impact: 'Medium Impact',
          impactType: 'warning',
          action: '#goals'
        },
        {
          id: 'act-3',
          title: 'Car Loan ₹2,000 Prepayment',
          desc: 'An extra monthly payment of ₹2,000 saves ₹18,400 interest and finishes 7 months early.',
          impact: 'High Impact',
          impactType: 'success',
          action: '#debts'
        }
      ]
    };
  }

  // Goals endpoints
  if (endpoint.startsWith('/goals')) {
    if (method === 'GET') {
      return db.goals;
    }
    if (method === 'POST') {
      const newGoal = {
        id: 'g-' + Date.now(),
        name: body.name || 'New Goal',
        category: body.category || 'General',
        targetAmount: Number(body.targetAmount) || 100000,
        currentSavings: Number(body.currentSavings) || 0,
        targetDate: body.targetDate || '2026-12-31',
        priority: body.priority || 'Medium'
      };
      db.goals.push(newGoal);
      saveMockDB(db);
      return newGoal;
    }
    if (method === 'PUT') {
      const id = endpoint.split('/')[2];
      db.goals = db.goals.map(g => g.id === id ? { ...g, ...body } : g);
      saveMockDB(db);
      return db.goals.find(g => g.id === id);
    }
    if (method === 'DELETE') {
      const id = endpoint.split('/')[2];
      db.goals = db.goals.filter(g => g.id !== id);
      saveMockDB(db);
      return { success: true };
    }
  }

  // Debts endpoints
  if (endpoint === '/debts') {
    const totalDebt = db.debts.reduce((sum, d) => sum + d.principal, 0);
    const totalEMI = db.debts.reduce((sum, d) => sum + d.emi, 0);
    const monthlyIncome = 105000;
    const dti = ((totalEMI / monthlyIncome) * 100).toFixed(1);

    return {
      totalDebt,
      totalMonthlyEMI: totalEMI,
      debtToIncomeRatio: parseFloat(dti),
      debts: db.debts
    };
  }

  if (endpoint === '/debts/simulate') {
    const extra = Number(body.extraPrepayment) || 0;
    const strategy = body.strategy || 'avalanche';
    // Realistic financial simulation
    const interestSaved = Math.round(extra * 42.5);
    const monthsSaved = Math.min(60, Math.round((extra / 1000) * 3.5));
    return {
      totalInterestSaved: interestSaved,
      monthsSaved: monthsSaved,
      originalTenure: 168,
      newTenure: Math.max(12, 168 - monthsSaved),
      strategy
    };
  }

  // Investment Recommendations
  if (endpoint === '/investments/recommendations') {
    return {
      riskAppetite: 'Moderate',
      allocations: [
        {
          instrument: 'Nifty 50 & Next 50 Index Mutual Funds',
          category: 'Equity',
          percentage: 45,
          expectedReturn: '12.0% - 13.5%',
          risk: 'High',
          rationale: 'Core wealth compounding engine to beat 6% retail inflation over 7+ years.',
          whyForYou: 'Matches your 15-year goal horizon for retirement corpus accumulation.'
        },
        {
          instrument: 'Public Provident Fund (PPF)',
          category: 'Fixed Income',
          percentage: 20,
          expectedReturn: '7.1% Tax-Free',
          risk: 'Low',
          rationale: 'Sovereign backed EEE status: deposit, interest, and maturity are 100% tax-free.',
          whyForYou: 'Provides guaranteed debt component and Section 80C deduction.'
        },
        {
          instrument: 'Sovereign Gold Bonds (SGB) / Gold ETF',
          category: 'Gold',
          percentage: 10,
          expectedReturn: '9.0% - 11.0%',
          risk: 'Moderate',
          rationale: 'Protects against Indian Rupee depreciation and macroeconomic tail risks.',
          whyForYou: 'Maintains an ideal 10% all-weather gold allocation.'
        },
        {
          instrument: 'National Pension System (NPS Tier 1)',
          category: 'Retirement',
          percentage: 15,
          expectedReturn: '10.5% - 12.0%',
          risk: 'Moderate',
          rationale: 'Exclusive additional tax deduction of ₹50,000 under Section 80CCD(1B).',
          whyForYou: 'Maximizes tax savings while building a dedicated retirement pension.'
        },
        {
          instrument: 'High-Yield Bank Fixed Deposits / Arbitrage Funds',
          category: 'Emergency / Cash',
          percentage: 10,
          expectedReturn: '7.0% - 7.5%',
          risk: 'Low',
          rationale: 'Guaranteed principal safety and instantaneous liquidity within 24 hours.',
          whyForYou: 'Maintains immediate access for medical and emergency needs.'
        }
      ]
    };
  }

  // Chatbot endpoints
  if (endpoint === '/chat/history') {
    return db.chatHistory;
  }

  if (endpoint === '/chat/message') {
    const userMsg = body.message || '';
    db.chatHistory.push({
      id: 'c-' + Date.now(),
      sender: 'user',
      text: userMsg,
      timestamp: new Date().toISOString()
    });

    let botReply = '';
    const lower = userMsg.toLowerCase();

    if (lower.includes('tax') || lower.includes('regime') || lower.includes('80c')) {
      botReply = `Under the Indian Income Tax guidelines for FY 2024-25:
• **New Tax Regime (Section 115BAC)**: Offers lower slab rates with a standard deduction of ₹75,000, zero tax on income up to ₹7.75 Lakhs, but disallows 80C deductions.
• **Old Tax Regime**: Beneficial if your total deductions (80C up to ₹1.5L, 80D health insurance up to ₹25k/₹50k, Home loan interest Section 24b up to ₹2L, NPS 80CCD up to ₹50k, and HRA) exceed approx ₹4.25 Lakhs.
Given your ₹2.2L home loan and PPF investments, the Old Regime could save you approximately ₹18,200 annually.`;
    } else if (lower.includes('prepay') || lower.includes('loan') || lower.includes('home loan')) {
      botReply = `Great question on prepayment! 
1. **Compare After-Tax Interest Rates**: If your SBI Home Loan is at 8.5% and you claim Section 24(b) interest deduction, your effective cost of borrowing is approximately ~6.0% (in the 30% bracket).
2. **Equity Compounding**: A diversified Nifty 50 Index Fund historically delivers ~12-13% CAGR over 7+ years.
3. **Recommendation**: Keep servicing your home loan EMI regularly while investing excess surplus into Equity SIPs. However, prepaying your high-interest **Credit Card (42%)** and **Car Loan (9.2%)** should be prioritized immediately!`;
    } else if (lower.includes('emergency') || lower.includes('cushion') || lower.includes('buffer')) {
      botReply = `A sound emergency fund in India should cover **6 months of essential living expenses**:
• Your monthly fixed & variable expenses: **₹75,500**
• Recommended 6-month target: **₹4,53,000**
• Your current liquid FD reserves: **₹3,40,000** (~4.5 months)
You are in good shape! Allocate ₹18,000/month for the next 6 months into high-interest flexi-FD or Arbitrage Funds to reach full coverage.`;
    } else {
      botReply = `Thank you for sharing that. As your ArthMitra advisor, I recommend maintaining a disciplined asset allocation of **60% Equity (Index Funds), 30% Debt/PPF/NPS, and 10% Gold**. Always ensure your Term Insurance (at least 15-20x annual income) and Health Insurance (₹10-15 Lakh family floater) are active before aggressive investing. Would you like a detailed breakdown of your savings or loan payoff timeline?`;
    }

    const assistantMsg = {
      id: 'c-' + (Date.now() + 1),
      sender: 'assistant',
      text: botReply,
      timestamp: new Date().toISOString()
    };
    db.chatHistory.push(assistantMsg);
    saveMockDB(db);

    return { reply: botReply };
  }

  // Reports
  if (endpoint === '/reports') {
    return db.reports;
  }

  if (endpoint === '/reports/generate') {
    const newReport = {
      id: 'rep-' + Date.now(),
      title: `${body.type || 'Custom'} Statement (${body.period || 'Current'})`,
      date: new Date().toISOString().split('T')[0],
      type: body.type || 'Summary',
      score: 74,
      status: 'Generated'
    };
    db.reports.unshift(newReport);
    saveMockDB(db);
    return newReport;
  }

  // Settings
  if (endpoint === '/settings') {
    return { status: 'success', settings: body };
  }

  return { status: 'ok' };
}

/**
 * Universal Fetch Wrapper
 * @param {string} endpoint 
 * @param {RequestInit} [options={}] 
 * @returns {Promise<{ data: any, error: string|null }>}
 */
export async function apiRequest(endpoint, options = {}) {
  // If in Mock Mode, intercept and resolve locally
  if (USE_MOCK) {
    try {
      const data = await handleMockRequest(endpoint, options);
      return { data, error: null };
    } catch (err) {
      return { data: null, error: err.message || 'Mock processing error' };
    }
  }

  const url = `${BASE_URL}${endpoint}`;
  const token = store.getState().token;

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    // Automatic 401 Unauthorized Handling
    if (response.status === 401) {
      store.clearAuth();
      window.location.hash = '#login';
      return { data: null, error: 'Session expired. Please log in again.' };
    }

    if (!response.ok) {
      let errMsg = `Server error (${response.status})`;
      try {
        const errorJson = await response.json();
        errMsg = errorJson.detail || errorJson.message || errMsg;
      } catch (e) { /* ignore text fallback */ }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      return { data: null, error: 'Request timed out after 15 seconds. Please try again.' };
    }
    return { data: null, error: 'Network error. Please check your connection or CORS settings.' };
  }
}
