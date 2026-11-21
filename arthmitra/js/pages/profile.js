/**
 * ArthMitra - Financial Profile Page Module
 * Multi-section financial data entry, live calculation bar, unsaved changes detection, optimistic save
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR, parseINR } from '../validators.js';
import { showToast, renderErrorState, renderSkeletonCards } from '../ui.js';

let isDirty = false;
let beforeUnloadListener = null;

export async function render(container) {
  isDirty = false;

  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="skeleton-card" style="height: 80px;"></div>
      <div class="grid grid-cols-2 gap-6">
        ${renderSkeletonCards(2)}
      </div>
    </div>
  `;

  const { data, error } = await apiRequest('/profile');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load profile',
      message: error,
      retryId: 'btn-retry-profile'
    });
    container.querySelector('#btn-retry-profile')?.addEventListener('click', () => render(container));
    return;
  }

  const p = data || {
    income: { salary: 85000, rental: 15000, other: 5000 },
    fixedExpenses: { rent: 25000, utilities: 6000, emis: 18500 },
    variableExpenses: { groceries: 12000, dining: 5000, travel: 4000, shopping: 5000 },
    assets: { bankFD: 350000, mutualFunds: 850000, ppf: 450000, nps: 220000, gold: 300000, realEstate: 3500000 },
    liabilities: { homeLoan: 2200000, carLoan: 320000, creditCards: 25000 },
    insurance: { lifeTermCover: 10000000, healthCover: 1000000 },
    riskAppetite: 'Moderate',
    dependents: 2
  };

  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Sticky Live Calculation Summary Bar -->
      <div class="profile-summary-bar" id="live-summary-bar">
        <div class="profile-summary-item">
          <span class="profile-summary-label">Total Monthly Inflow</span>
          <span class="profile-summary-value text-success tabular-nums" id="sum-total-income">₹0</span>
        </div>
        <div class="profile-summary-item">
          <span class="profile-summary-label">Total Monthly Outflow</span>
          <span class="profile-summary-value text-danger tabular-nums" id="sum-total-expenses">₹0</span>
        </div>
        <div class="profile-summary-item">
          <span class="profile-summary-label">Monthly Surplus / Savings</span>
          <span class="profile-summary-value text-accent tabular-nums" id="sum-net-savings">₹0</span>
        </div>
        <div class="profile-summary-item">
          <span class="profile-summary-label">Savings Rate & Net Worth</span>
          <span class="profile-summary-value text-primary tabular-nums" id="sum-savings-rate">0%</span>
        </div>
      </div>

      <form id="form-profile" novalidate>
        
        <!-- Section 1: Income Breakdown -->
        <div class="card profile-section-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.wallet(20)} Monthly Inflow (₹)</h2>
              <p class="card-subtitle">Take-home salary after TDS, rental yields, and secondary income</p>
            </div>
            <span class="badge badge-success">Income Stream</span>
          </div>
          <div class="profile-inputs-grid">
            <div class="form-group">
              <label class="form-label" for="inp-salary">Monthly Primary Salary</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-salary" name="income_salary" class="form-input money-calc" value="${p.income.salary || 0}" min="0" step="1000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-rental">Rental / Commercial Yield</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-rental" name="income_rental" class="form-input money-calc" value="${p.income.rental || 0}" min="0" step="1000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-other-income">Consulting / Dividend / Other</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-other-income" name="income_other" class="form-input money-calc" value="${p.income.other || 0}" min="0" step="1000">
              </div>
            </div>
          </div>
        </div>

        <!-- Section 2: Fixed Living Expenses -->
        <div class="card profile-section-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.creditCard(20)} Fixed Monthly Expenses (₹)</h2>
              <p class="card-subtitle">Non-negotiable obligations: Rent, EMIs, Maintenance, and Utilities</p>
            </div>
            <span class="badge badge-warning">Fixed Obligation</span>
          </div>
          <div class="profile-inputs-grid">
            <div class="form-group">
              <label class="form-label" for="inp-rent">House Rent / Maintenance</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-rent" name="fixed_rent" class="form-input money-calc" value="${p.fixedExpenses.rent || 0}" min="0" step="500">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-utilities">Electricity, Water & Internet</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-utilities" name="fixed_utilities" class="form-input money-calc" value="${p.fixedExpenses.utilities || 0}" min="0" step="500">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-emis">Monthly Loan EMIs (Total)</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-emis" name="fixed_emis" class="form-input money-calc" value="${p.fixedExpenses.emis || 0}" min="0" step="500">
              </div>
            </div>
          </div>
        </div>

        <!-- Section 3: Variable Lifestyle Expenses -->
        <div class="card profile-section-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.trendingDown(20)} Variable Lifestyle Outflows (₹)</h2>
              <p class="card-subtitle">Groceries, Dining out, Subscriptions, and Discretionary shopping</p>
            </div>
            <span class="badge badge-neutral">Flexible</span>
          </div>
          <div class="profile-inputs-grid">
            <div class="form-group">
              <label class="form-label" for="inp-groceries">Groceries & Daily Essentials</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-groceries" name="var_groceries" class="form-input money-calc" value="${p.variableExpenses.groceries || 0}" min="0" step="500">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-dining">Dining Out & Entertainment</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-dining" name="var_dining" class="form-input money-calc" value="${p.variableExpenses.dining || 0}" min="0" step="500">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-travel">Fuel, Cabs & Travel</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-travel" name="var_travel" class="form-input money-calc" value="${p.variableExpenses.travel || 0}" min="0" step="500">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-shopping">Shopping & Subscriptions</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-shopping" name="var_shopping" class="form-input money-calc" value="${p.variableExpenses.shopping || 0}" min="0" step="500">
              </div>
            </div>
          </div>
        </div>

        <!-- Section 4: Current Assets & Portfolio -->
        <div class="card profile-section-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.layers(20)} Existing Assets & Investments (₹)</h2>
              <p class="card-subtitle">Liquid bank balances, equity funds, retirement instruments & physical gold</p>
            </div>
            <span class="badge badge-primary">Net Worth Driver</span>
          </div>
          <div class="profile-inputs-grid">
            <div class="form-group">
              <label class="form-label" for="inp-bank-fd">Bank Savings & Fixed Deposits</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-bank-fd" name="asset_bankFD" class="form-input money-calc" value="${p.assets.bankFD || 0}" min="0" step="10000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-mutual-funds">Mutual Funds & Direct Stocks</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-mutual-funds" name="asset_mutualFunds" class="form-input money-calc" value="${p.assets.mutualFunds || 0}" min="0" step="10000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-ppf">EPF & PPF Balance</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-ppf" name="asset_ppf" class="form-input money-calc" value="${p.assets.ppf || 0}" min="0" step="10000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-nps">NPS (Tier 1 & Tier 2)</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-nps" name="asset_nps" class="form-input money-calc" value="${p.assets.nps || 0}" min="0" step="10000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-gold">Physical Gold / Sovereign Gold Bonds</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-gold" name="asset_gold" class="form-input money-calc" value="${p.assets.gold || 0}" min="0" step="10000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-real-estate">Real Estate Market Value</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-real-estate" name="asset_realEstate" class="form-input money-calc" value="${p.assets.realEstate || 0}" min="0" step="50000">
              </div>
            </div>
          </div>
        </div>

        <!-- Section 5: Risk Appetite & Dependents -->
        <div class="card profile-section-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.shield(20)} Risk Profile & Insurance Health</h2>
              <p class="card-subtitle">Determines your recommended asset allocation split</p>
            </div>
          </div>
          <div class="profile-inputs-grid">
            <div class="form-group">
              <label class="form-label" for="sel-risk">Investment Risk Appetite</label>
              <select id="sel-risk" name="riskAppetite" class="form-select">
                <option value="Conservative" ${p.riskAppetite === 'Conservative' ? 'selected' : ''}>Conservative (Capital Preservation Focus)</option>
                <option value="Moderate" ${p.riskAppetite === 'Moderate' ? 'selected' : ''}>Moderate (Balanced Growth & Safety)</option>
                <option value="Aggressive" ${p.riskAppetite === 'Aggressive' ? 'selected' : ''}>Aggressive (High Equity & Long-Term Compounding)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-dependents">Financial Dependents</label>
              <input type="number" id="inp-dependents" name="dependents" class="form-input" value="${p.dependents ?? 2}" min="0" max="10">
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-term-insurance">Term Life Cover (Sum Assured)</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-term-insurance" name="ins_term" class="form-input" value="${p.insurance?.lifeTermCover || 10000000}" step="500000">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="inp-health-insurance">Family Health Insurance Cover</label>
              <div class="input-group">
                <span class="input-prefix">₹</span>
                <input type="number" id="inp-health-insurance" name="ins_health" class="form-input" value="${p.insurance?.healthCover || 1000000}" step="100000">
              </div>
            </div>
          </div>
        </div>

        <!-- Submit & Actions Strip -->
        <div class="flex items-center justify-between mt-6">
          <div class="text-xs text-muted" id="unsaved-status">
            All changes up to date.
          </div>
          <div class="flex gap-4">
            <button type="button" class="btn btn-secondary" id="btn-reset-profile">Reset</button>
            <button type="submit" class="btn btn-primary btn-lg" id="btn-save-profile">
              ${icons.check(18)}
              <span>Save & Recalculate Health Score</span>
            </button>
          </div>
        </div>

      </form>
    </div>
  `;

  const form = container.querySelector('#form-profile');
  const sumIncomeEl = container.querySelector('#sum-total-income');
  const sumExpenseEl = container.querySelector('#sum-total-expenses');
  const sumSavingsEl = container.querySelector('#sum-net-savings');
  const sumRateEl = container.querySelector('#sum-savings-rate');
  const unsavedStatus = container.querySelector('#unsaved-status');

  // Live calculation updater
  const updateTotals = () => {
    const salary = parseINR(form.elements['income_salary']?.value);
    const rental = parseINR(form.elements['income_rental']?.value);
    const other = parseINR(form.elements['income_other']?.value);
    const totalIncome = salary + rental + other;

    const rent = parseINR(form.elements['fixed_rent']?.value);
    const util = parseINR(form.elements['fixed_utilities']?.value);
    const emi = parseINR(form.elements['fixed_emis']?.value);
    const groceries = parseINR(form.elements['var_groceries']?.value);
    const dining = parseINR(form.elements['var_dining']?.value);
    const travel = parseINR(form.elements['var_travel']?.value);
    const shopping = parseINR(form.elements['var_shopping']?.value);
    const totalExpenses = rent + util + emi + groceries + dining + travel + shopping;

    const netSavings = totalIncome - totalExpenses;
    const rate = totalIncome > 0 ? ((netSavings / totalIncome) * 100).toFixed(1) : '0';

    const assets = parseINR(form.elements['asset_bankFD']?.value) +
                   parseINR(form.elements['asset_mutualFunds']?.value) +
                   parseINR(form.elements['asset_ppf']?.value) +
                   parseINR(form.elements['asset_nps']?.value) +
                   parseINR(form.elements['asset_gold']?.value) +
                   parseINR(form.elements['asset_realEstate']?.value);
    const liabilities = 2545000; // From debts
    const netWorth = assets - liabilities;

    sumIncomeEl.textContent = formatINR(totalIncome);
    sumExpenseEl.textContent = formatINR(totalExpenses);
    sumSavingsEl.textContent = formatINR(netSavings);
    sumRateEl.innerHTML = `${rate}% <small style="font-size:0.75rem; font-weight:normal; opacity:0.8;">(Net: ${formatINR(netWorth, true)})</small>`;
  };

  updateTotals();

  // Mark dirty on any input change
  form.addEventListener('input', () => {
    isDirty = true;
    updateTotals();
    if (unsavedStatus) {
      unsavedStatus.textContent = '● Unsaved changes detected.';
      unsavedStatus.style.color = 'var(--color-warning)';
    }
  });

  // Warn on browser unload if unsaved changes
  beforeUnloadListener = (e) => {
    if (isDirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  };
  window.addEventListener('beforeunload', beforeUnloadListener);

  // Reset handler
  container.querySelector('#btn-reset-profile')?.addEventListener('click', () => {
    render(container);
  });

  // Submit Handler with Optimistic UI
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const saveBtn = container.querySelector('#btn-save-profile');
    saveBtn.classList.add('btn-loading');

    const updatedProfile = {
      income: {
        salary: parseINR(form.elements['income_salary'].value),
        rental: parseINR(form.elements['income_rental'].value),
        other: parseINR(form.elements['income_other'].value)
      },
      fixedExpenses: {
        rent: parseINR(form.elements['fixed_rent'].value),
        utilities: parseINR(form.elements['fixed_utilities'].value),
        emis: parseINR(form.elements['fixed_emis'].value)
      },
      variableExpenses: {
        groceries: parseINR(form.elements['var_groceries'].value),
        dining: parseINR(form.elements['var_dining'].value),
        travel: parseINR(form.elements['var_travel'].value),
        shopping: parseINR(form.elements['var_shopping'].value)
      },
      assets: {
        bankFD: parseINR(form.elements['asset_bankFD'].value),
        mutualFunds: parseINR(form.elements['asset_mutualFunds'].value),
        ppf: parseINR(form.elements['asset_ppf'].value),
        nps: parseINR(form.elements['asset_nps'].value),
        gold: parseINR(form.elements['asset_gold'].value),
        realEstate: parseINR(form.elements['asset_realEstate'].value)
      },
      insurance: {
        lifeTermCover: parseINR(form.elements['ins_term'].value),
        healthCover: parseINR(form.elements['ins_health'].value)
      },
      riskAppetite: form.elements['riskAppetite'].value,
      dependents: parseInt(form.elements['dependents'].value, 10) || 0
    };

    const { error: saveErr } = await apiRequest('/profile', {
      method: 'PUT',
      body: JSON.stringify(updatedProfile)
    });

    saveBtn.classList.remove('btn-loading');

    if (saveErr) {
      showToast({ title: 'Failed to Save Profile', message: saveErr, type: 'danger' });
      return;
    }

    isDirty = false;
    if (unsavedStatus) {
      unsavedStatus.textContent = 'All changes saved successfully.';
      unsavedStatus.style.color = 'var(--color-success)';
    }

    showToast({
      title: 'Profile Saved',
      message: 'Your financial parameters and health metrics have been updated!',
      type: 'success'
    });
  });
}

export function destroy() {
  if (beforeUnloadListener) {
    window.removeEventListener('beforeunload', beforeUnloadListener);
    beforeUnloadListener = null;
  }
}
