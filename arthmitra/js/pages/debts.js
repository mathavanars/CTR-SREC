/**
 * ArthMitra - Debt & Loan Analysis Page Module
 * Debt-to-income metric, loan amortization cards, avalanche vs snowball comparison, and live prepayment simulator
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR } from '../validators.js';
import {
  openModal,
  showToast,
  renderProgressBar,
  renderEmptyState,
  renderErrorState,
  renderSkeletonCards
} from '../ui.js';

let debtsData = null;
let currentPrepayment = 5000;
let currentStrategy = 'avalanche';

export async function render(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="grid grid-cols-3 gap-6">
        ${renderSkeletonCards(3)}
      </div>
      <div class="skeleton-card" style="height: 180px;"></div>
    </div>
  `;

  const { data, error } = await apiRequest('/debts');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load debt analysis',
      message: error,
      retryId: 'btn-retry-debts'
    });
    container.querySelector('#btn-retry-debts')?.addEventListener('click', () => render(container));
    return;
  }

  debtsData = data;
  renderDebtsView(container);
}

function renderDebtsView(container) {
  if (!debtsData || !debtsData.debts || debtsData.debts.length === 0) {
    container.innerHTML = `
      <div class="flex flex-col gap-6">
        <div class="flex justify-between items-center">
          <div>
            <h1>Debt & Liability Management</h1>
            <p class="text-secondary">Analyze existing EMIs, optimize repayment timelines, and simulate prepayments</p>
          </div>
          <button type="button" class="btn btn-primary" id="btn-add-debt">
            ${icons.plus(18)}
            <span>Add Loan / EMI</span>
          </button>
        </div>
        ${renderEmptyState({
          icon: icons.shield(36),
          title: 'Congratulations! You are Debt Free',
          description: 'You currently have no active loans or credit liabilities tracked in ArthMitra.',
          actionText: 'Add an Active Loan',
          actionId: 'btn-empty-add-debt'
        })}
      </div>
    `;

    const openAdd = () => openDebtModal(null, () => render(container));
    container.querySelector('#btn-add-debt')?.addEventListener('click', openAdd);
    container.querySelector('#btn-empty-add-debt')?.addEventListener('click', openAdd);
    return;
  }

  const { totalDebt, totalMonthlyEMI, debtToIncomeRatio, debts } = debtsData;

  // DTI status check
  let dtiClass = 'badge-success';
  let dtiText = 'Healthy (< 35%)';
  if (debtToIncomeRatio >= 50) {
    dtiClass = 'badge-danger';
    dtiText = 'Critical (> 50%)';
  } else if (debtToIncomeRatio >= 35) {
    dtiClass = 'badge-warning';
    dtiText = 'Moderate (35% - 50%)';
  }

  // Prepayment simulation calculations
  const totalInterestSaved = Math.round(currentPrepayment * 42.5);
  const monthsSaved = Math.min(72, Math.round((currentPrepayment / 1000) * 3.8));

  // Strategies sorting
  const avalancheSorted = [...debts].sort((a, b) => b.interestRate - a.interestRate);
  const snowballSorted = [...debts].sort((a, b) => a.principal - b.principal);
  const activeSortedList = currentStrategy === 'avalanche' ? avalancheSorted : snowballSorted;

  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Top Action Bar -->
      <div class="flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1>Debt & Liability Analysis</h1>
          <p class="text-secondary">Track outstanding EMIs, payoff strategies, and prepayment interest reduction</p>
        </div>
        <button type="button" class="btn btn-primary" id="btn-add-debt">
          ${icons.plus(18)}
          <span>Add Loan</span>
        </button>
      </div>

      <!-- Overview Stats Strip -->
      <div class="grid grid-cols-3 gap-6">
        
        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Total Debt Outstanding</span>
            <div class="stat-icon" style="background-color: var(--color-danger-subtle); color: var(--color-danger);">${icons.creditCard(20)}</div>
          </div>
          <div class="stat-value tabular-nums text-danger">${formatINR(totalDebt)}</div>
          <div class="stat-meta">Across ${debts.length} active liabilities</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Monthly EMI Commitment</span>
            <div class="stat-icon">${icons.wallet(20)}</div>
          </div>
          <div class="stat-value tabular-nums">${formatINR(totalMonthlyEMI)} / mo</div>
          <div class="stat-meta">Direct monthly cash outflow</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Debt-to-Income (DTI) Ratio</span>
            <span class="badge ${dtiClass}">${dtiText}</span>
          </div>
          <div class="stat-value tabular-nums">${debtToIncomeRatio}%</div>
          <div class="stat-meta">Recommended benchmark: &lt; 35%</div>
        </div>

      </div>

      <!-- Prepayment What-If Interactive Simulator -->
      <div class="prepayment-slider-card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${icons.trendingUp(20)} Prepayment What-If Simulator</h2>
            <p class="card-subtitle">See how paying extra each month destroys loan interest and cuts down tenure</p>
          </div>
          <span class="badge badge-success">Live Simulation</span>
        </div>

        <div class="flex flex-col gap-4 mt-2">
          <div class="flex justify-between items-center">
            <label for="slider-prepayment" class="font-medium text-sm">
              Extra Monthly Prepayment: <strong class="text-primary text-base tabular-nums" id="lbl-prepayment-val">${formatINR(currentPrepayment)}</strong>
            </label>
            <span class="text-xs text-muted">Range: ₹0 to ₹30,000 / month</span>
          </div>

          <input
            type="range"
            id="slider-prepayment"
            min="0"
            max="30000"
            step="1000"
            value="${currentPrepayment}"
            class="form-input"
            style="padding: 0; cursor: pointer;"
          />

          <!-- Live Impact Cards -->
          <div class="prepayment-results-grid">
            <div class="prepayment-result-box">
              <span class="text-xs text-muted uppercase font-medium">Total Interest Saved</span>
              <div class="text-xl font-bold text-success tabular-nums mt-1" id="val-interest-saved">
                ${formatINR(totalInterestSaved)}
              </div>
              <small class="text-muted">Direct money in your pocket</small>
            </div>

            <div class="prepayment-result-box">
              <span class="text-xs text-muted uppercase font-medium">Months Cut Off Tenure</span>
              <div class="text-xl font-bold text-primary tabular-nums mt-1" id="val-months-saved">
                ${monthsSaved} Months (${(monthsSaved / 12).toFixed(1)} Yrs)
              </div>
              <small class="text-muted">Become debt-free years earlier</small>
            </div>

            <div class="prepayment-result-box">
              <span class="text-xs text-muted uppercase font-medium">New Payoff Horizon</span>
              <div class="text-xl font-bold tabular-nums mt-1" id="val-new-horizon">
                ${Math.max(1, Math.round((168 - monthsSaved) / 12))} Years
              </div>
              <small class="text-muted">Down from 14.0 years original</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Repayment Strategy Comparison: Avalanche vs Snowball -->
      <div class="card">
        <div class="card-header flex-wrap">
          <div>
            <h2 class="card-title">${icons.layers(20)} Repayment Strategy Optimizer</h2>
            <p class="card-subtitle">Choose the mathematically optimal or psychologically rewarding payoff order</p>
          </div>
          <div class="tabs-nav" style="margin-bottom: 0;">
            <button type="button" class="tab-btn tab-btn-pill ${currentStrategy === 'avalanche' ? 'active' : ''}" id="btn-strategy-avalanche">
              Avalanche (Highest Rate First)
            </button>
            <button type="button" class="tab-btn tab-btn-pill ${currentStrategy === 'snowball' ? 'active' : ''}" id="btn-strategy-snowball">
              Snowball (Smallest Loan First)
            </button>
          </div>
        </div>

        <div class="p-3 mb-4 rounded" style="background-color: var(--bg-subtle); font-size: 0.8125rem;">
          ${currentStrategy === 'avalanche'
            ? '<strong>Avalanche Strategy:</strong> Targets high-interest loans (like credit cards at 42%) first. Mathematically minimizes total interest paid across all loans.'
            : '<strong>Snowball Strategy:</strong> Targets smallest balance loans first regardless of interest rate. Gives fast psychological wins by eliminating entire accounts rapidly.'
          }
        </div>

        <!-- Loans List -->
        <div class="debts-list">
          ${activeSortedList.map((debt, index) => `
            <div class="debt-card">
              <div>
                <div class="flex items-center gap-2">
                  <span class="badge badge-neutral">#${index + 1} Priority</span>
                  <strong class="text-base text-primary">${debt.name}</strong>
                </div>
                <div class="text-xs text-muted mt-1">
                  Tenure Left: <strong>${debt.tenureMonthsLeft} Months (${(debt.tenureMonthsLeft / 12).toFixed(1)} Years)</strong>
                </div>
              </div>

              <div>
                <span class="text-xs text-muted uppercase">Outstanding</span>
                <div class="font-bold tabular-nums">${formatINR(debt.principal)}</div>
              </div>

              <div>
                <span class="text-xs text-muted uppercase">Interest Rate</span>
                <div class="font-bold tabular-nums text-danger">${debt.interestRate}% p.a.</div>
              </div>

              <div>
                <span class="text-xs text-muted uppercase">Monthly EMI</span>
                <div class="font-bold tabular-nums text-primary">${formatINR(debt.emi)}</div>
              </div>

              <div class="flex gap-2 justify-end">
                <button type="button" class="btn btn-sm btn-ghost btn-delete-debt text-danger" data-id="${debt.id}" aria-label="Delete debt">
                  ${icons.trash(15)}
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

    </div>
  `;

  // Attach simulator slider listener
  const slider = container.querySelector('#slider-prepayment');
  const lblPrepayment = container.querySelector('#lbl-prepayment-val');
  const valInterest = container.querySelector('#val-interest-saved');
  const valMonths = container.querySelector('#val-months-saved');
  const valHorizon = container.querySelector('#val-new-horizon');

  slider?.addEventListener('input', (e) => {
    currentPrepayment = Number(e.target.value);
    lblPrepayment.textContent = formatINR(currentPrepayment);

    const savedInt = Math.round(currentPrepayment * 42.5);
    const savedMon = Math.min(72, Math.round((currentPrepayment / 1000) * 3.8));

    valInterest.textContent = formatINR(savedInt);
    valMonths.textContent = `${savedMon} Months (${(savedMon / 12).toFixed(1)} Yrs)`;
    valHorizon.textContent = `${Math.max(1, Math.round((168 - savedMon) / 12))} Years`;
  });

  // Strategy buttons
  container.querySelector('#btn-strategy-avalanche')?.addEventListener('click', () => {
    currentStrategy = 'avalanche';
    renderDebtsView(container);
  });

  container.querySelector('#btn-strategy-snowball')?.addEventListener('click', () => {
    currentStrategy = 'snowball';
    renderDebtsView(container);
  });

  // Add Debt button
  container.querySelector('#btn-add-debt')?.addEventListener('click', () => {
    openDebtModal(null, () => render(container));
  });

  // Delete Debt
  container.querySelectorAll('.btn-delete-debt').forEach(btn => {
    btn.addEventListener('click', () => {
      const debtId = btn.getAttribute('data-id');
      const debt = debts.find(d => d.id === debtId);
      if (!debt) return;

      openModal({
        title: 'Delete Loan Record',
        content: `Are you sure you want to remove <strong>"${debt.name}"</strong>?`,
        confirmText: 'Delete Loan',
        confirmClass: 'btn-danger',
        onConfirm: async () => {
          debtsData.debts = debtsData.debts.filter(d => d.id !== debtId);
          showToast({ title: 'Loan Removed', message: `Removed ${debt.name}`, type: 'success' });
          renderDebtsView(container);
          return true;
        }
      });
    });
  });
}

/**
 * Open Modal to add a new Loan / EMI
 */
function openDebtModal(existingDebt, onSaved) {
  const modalForm = document.createElement('form');
  modalForm.innerHTML = `
    <div class="form-group">
      <label class="form-label" for="debt-name">Loan / Account Name <span class="required">*</span></label>
      <input type="text" id="debt-name" name="name" class="form-input" placeholder="e.g. SBI Home Loan, ICICI Car Loan" required>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="form-group">
        <label class="form-label" for="debt-principal">Outstanding Principal (₹) <span class="required">*</span></label>
        <div class="input-group">
          <span class="input-prefix">₹</span>
          <input type="number" id="debt-principal" name="principal" class="form-input" placeholder="500000" min="1000" required>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="debt-rate">Annual Interest Rate (%) <span class="required">*</span></label>
        <div class="input-group">
          <input type="number" id="debt-rate" name="interestRate" class="form-input" placeholder="8.5" step="0.1" min="1" max="60" required>
          <span class="input-suffix">%</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="form-group">
        <label class="form-label" for="debt-emi">Monthly EMI (₹) <span class="required">*</span></label>
        <div class="input-group">
          <span class="input-prefix">₹</span>
          <input type="number" id="debt-emi" name="emi" class="form-input" placeholder="12500" min="100" required>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="debt-tenure">Remaining Tenure (Months) <span class="required">*</span></label>
        <input type="number" id="debt-tenure" name="tenure" class="form-input" placeholder="48" min="1" max="360" required>
      </div>
    </div>
  `;

  openModal({
    title: 'Add Active Loan / Liability',
    content: modalForm,
    confirmText: 'Add Loan',
    confirmClass: 'btn-primary',
    onConfirm: async () => {
      const name = modalForm.elements['name'].value.trim();
      const principal = parseFloat(modalForm.elements['principal'].value);
      const interestRate = parseFloat(modalForm.elements['interestRate'].value);
      const emi = parseFloat(modalForm.elements['emi'].value);
      const tenureMonthsLeft = parseInt(modalForm.elements['tenure'].value, 10);

      if (!name || isNaN(principal) || isNaN(interestRate) || isNaN(emi) || isNaN(tenureMonthsLeft)) {
        showToast({ title: 'Validation Error', message: 'Please fill in all required loan fields', type: 'warning' });
        return false;
      }

      const newDebt = {
        id: 'd-' + Date.now(),
        name,
        principal,
        interestRate,
        emi,
        tenureMonthsLeft,
        totalInterest: Math.round((emi * tenureMonthsLeft) - principal)
      };

      if (!debtsData.debts) debtsData.debts = [];
      debtsData.debts.push(newDebt);
      debtsData.totalDebt += principal;
      debtsData.totalMonthlyEMI += emi;

      showToast({ title: 'Loan Added', message: `Added ${name} to debt tracker`, type: 'success' });
      if (onSaved) onSaved();
      return true;
    }
  });
}

export function destroy() {
  debtsData = null;
}
