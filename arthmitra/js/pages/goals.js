/**
 * ArthMitra - Goal Planning Page Module
 * Create, edit, and track personal financial milestones with SIP calculations and timeline cards
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR, isFutureDate } from '../validators.js';
import {
  openModal,
  closeModal,
  showToast,
  renderProgressBar,
  renderEmptyState,
  renderErrorState,
  renderSkeletonCards
} from '../ui.js';

let goalsData = [];
let sortOrder = 'date'; // 'date' | 'priority' | 'progress'

/**
 * Calculate recommended monthly SIP to reach target by targetDate assuming 12% equity CAGR
 */
function calculateMonthlySIP(targetAmount, currentSavings, targetDateStr) {
  const target = Number(targetAmount);
  const current = Number(currentSavings);
  const deficit = Math.max(0, target - current);
  if (deficit <= 0) return 0;

  const targetDate = new Date(targetDateStr);
  const now = new Date();
  const monthsDiff = Math.max(1, Math.round((targetDate - now) / (1000 * 60 * 60 * 24 * 30.4375)));

  // Future value of existing savings at 12% p.a. (1% monthly)
  const r = 0.12 / 12;
  const fvCurrent = current * Math.pow(1 + r, monthsDiff);
  const netDeficit = Math.max(0, target - fvCurrent);

  if (netDeficit <= 0) return 0;

  // Monthly SIP formula: FV = P * [((1 + r)^n - 1) / r] * (1 + r)
  const factor = ((Math.pow(1 + r, monthsDiff) - 1) / r) * (1 + r);
  return Math.round(netDeficit / factor);
}

/**
 * Determine goal progress health status
 */
function getGoalHealthStatus(current, target, targetDateStr) {
  const pct = target > 0 ? (current / target) * 100 : 0;
  const targetDate = new Date(targetDateStr);
  const totalMonths = 36; // nominal baseline
  const monthsLeft = Math.max(1, (targetDate - new Date()) / (1000 * 60 * 60 * 24 * 30));

  if (pct >= 85 || (pct >= 50 && monthsLeft >= 18)) {
    return { label: 'On-Track', badgeClass: 'badge-success' };
  } else if (pct >= 35 || monthsLeft >= 12) {
    return { label: 'At-Risk', badgeClass: 'badge-warning' };
  }
  return { label: 'Behind', badgeClass: 'badge-danger' };
}

export async function render(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="flex justify-between items-center">
        <div class="skeleton skeleton-text" style="width: 200px; height: 32px;"></div>
        <div class="skeleton skeleton-text" style="width: 140px; height: 36px;"></div>
      </div>
      <div class="grid grid-cols-3 gap-6">
        ${renderSkeletonCards(3)}
      </div>
    </div>
  `;

  const { data, error } = await apiRequest('/goals');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load goals',
      message: error,
      retryId: 'btn-retry-goals'
    });
    container.querySelector('#btn-retry-goals')?.addEventListener('click', () => render(container));
    return;
  }

  goalsData = data || [];
  renderGoalsView(container);
}

function renderGoalsView(container) {
  if (!goalsData || goalsData.length === 0) {
    container.innerHTML = `
      <div class="flex flex-col gap-6">
        <div class="flex justify-between items-center">
          <div>
            <h1>Life Milestone Goals</h1>
            <p class="text-secondary">Plan your future corpus with compound interest projections</p>
          </div>
          <button type="button" class="btn btn-primary" id="btn-create-goal">
            ${icons.plus(18)}
            <span>Add New Goal</span>
          </button>
        </div>
        ${renderEmptyState({
          icon: icons.target(36),
          title: 'No Financial Goals Configured',
          description: 'Define your first target such as a 6-month Emergency Cushion, Home Down Payment, or Child Education.',
          actionText: 'Create Your First Goal',
          actionId: 'btn-empty-create-goal'
        })}
      </div>
    `;

    const openCreate = () => openGoalModal(null, () => render(container));
    container.querySelector('#btn-create-goal')?.addEventListener('click', openCreate);
    container.querySelector('#btn-empty-create-goal')?.addEventListener('click', openCreate);
    return;
  }

  // Calculate summary metrics
  const totalTargeted = goalsData.reduce((acc, g) => acc + Number(g.targetAmount), 0);
  const totalSaved = goalsData.reduce((acc, g) => acc + Number(g.currentSavings), 0);
  const overallPct = totalTargeted > 0 ? Math.round((totalSaved / totalTargeted) * 100) : 0;

  // Sort goals
  const sortedGoals = [...goalsData].sort((a, b) => {
    if (sortOrder === 'date') return new Date(a.targetDate) - new Date(b.targetDate);
    if (sortOrder === 'priority') {
      const pWeights = { 'High': 3, 'Medium': 2, 'Low': 1 };
      return (pWeights[b.priority] || 0) - (pWeights[a.priority] || 0);
    }
    const pctA = (a.currentSavings / a.targetAmount) || 0;
    const pctB = (b.currentSavings / b.targetAmount) || 0;
    return pctB - pctA;
  });

  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Top Action Bar -->
      <div class="flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1>Financial Goal Planning</h1>
          <p class="text-secondary">Target corpus, SIP monthly breakdown & projected timeline</p>
        </div>
        <div class="flex items-center gap-3">
          <select id="sel-sort-goals" class="form-select" style="width: auto;">
            <option value="date" ${sortOrder === 'date' ? 'selected' : ''}>Sort by: Target Date</option>
            <option value="priority" ${sortOrder === 'priority' ? 'selected' : ''}>Sort by: Priority</option>
            <option value="progress" ${sortOrder === 'progress' ? 'selected' : ''}>Sort by: Completion %</option>
          </select>
          <button type="button" class="btn btn-primary" id="btn-create-goal">
            ${icons.plus(18)}
            <span>Add New Goal</span>
          </button>
        </div>
      </div>

      <!-- Goal Portfolio Summary Banner -->
      <div class="card card-gradient-primary">
        <div class="flex justify-between items-center flex-wrap gap-6">
          <div>
            <span class="text-xs text-muted uppercase font-semibold">Total Target Milestones</span>
            <div class="text-2xl font-bold tabular-nums text-primary">${formatINR(totalTargeted)}</div>
          </div>
          <div>
            <span class="text-xs text-muted uppercase font-semibold">Accumulated Corpus</span>
            <div class="text-2xl font-bold tabular-nums text-success">${formatINR(totalSaved)}</div>
          </div>
          <div>
            <span class="text-xs text-muted uppercase font-semibold">Overall Funded</span>
            <div class="text-2xl font-bold tabular-nums">${overallPct}%</div>
          </div>
          <div style="flex: 1; max-width: 320px;">
            ${renderProgressBar({
              current: totalSaved,
              target: totalTargeted,
              variant: 'success'
            })}
          </div>
        </div>
      </div>

      <!-- Goals Grid Cards -->
      <div class="goals-grid">
        ${sortedGoals.map(goal => {
          const sipNeeded = calculateMonthlySIP(goal.targetAmount, goal.currentSavings, goal.targetDate);
          const status = getGoalHealthStatus(goal.currentSavings, goal.targetAmount, goal.targetDate);
          const percent = goal.targetAmount > 0 ? Math.min(100, Math.round((goal.currentSavings / goal.targetAmount) * 100)) : 0;

          let categoryIcon = icons.target(22);
          if (goal.category === 'House') categoryIcon = icons.wallet(22);
          if (goal.category === 'Vehicle') categoryIcon = icons.creditCard(22);
          if (goal.category === 'Emergency') categoryIcon = icons.shield(22);

          const priorityBadgeClass = goal.priority === 'High' ? 'badge-danger' : (goal.priority === 'Medium' ? 'badge-warning' : 'badge-neutral');

          return `
            <div class="goal-card" data-id="${goal.id}">
              <div class="goal-header">
                <div class="goal-category-icon">${categoryIcon}</div>
                <div class="goal-details">
                  <div class="flex items-center justify-between gap-2">
                    <h3 class="goal-name">${goal.name}</h3>
                    <span class="badge ${priorityBadgeClass}">${goal.priority}</span>
                  </div>
                  <div class="goal-target-date">
                    Target Date: <strong class="text-secondary">${new Date(goal.targetDate).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}</strong>
                  </div>
                </div>
              </div>

              <!-- Progress Section -->
              <div>
                <div class="flex justify-between items-center text-xs mb-2">
                  <span class="text-muted">Saved: <strong>${formatINR(goal.currentSavings)}</strong></span>
                  <span class="font-bold tabular-nums">${percent}%</span>
                </div>
                ${renderProgressBar({
                  current: goal.currentSavings,
                  target: goal.targetAmount,
                  variant: percent >= 75 ? 'success' : (percent >= 35 ? 'primary' : 'warning')
                })}
                <div class="flex justify-between items-center text-xs mt-1 text-muted">
                  <span>Goal: ${formatINR(goal.targetAmount)}</span>
                  <span class="badge ${status.badgeClass}">${status.label}</span>
                </div>
              </div>

              <!-- Monthly SIP Needed -->
              <div class="goal-sip-badge">
                <span>Recommended SIP:</span>
                <strong class="tabular-nums">${formatINR(sipNeeded)} / mo</strong>
              </div>

              <!-- Actions -->
              <div class="flex justify-end gap-2 mt-2 pt-3" style="border-top: 1px solid var(--border-subtle);">
                <button type="button" class="btn btn-sm btn-ghost btn-edit-goal" data-id="${goal.id}" aria-label="Edit goal">
                  ${icons.edit(15)}
                  <span>Edit</span>
                </button>
                <button type="button" class="btn btn-sm btn-ghost text-danger btn-delete-goal" data-id="${goal.id}" aria-label="Delete goal">
                  ${icons.trash(15)}
                  <span>Delete</span>
                </button>
              </div>
            </div>
          `;
        }).join('')}
      </div>

    </div>
  `;

  // Event handlers
  container.querySelector('#btn-create-goal')?.addEventListener('click', () => {
    openGoalModal(null, () => render(container));
  });

  container.querySelector('#sel-sort-goals')?.addEventListener('change', (e) => {
    sortOrder = e.target.value;
    renderGoalsView(container);
  });

  container.querySelectorAll('.btn-edit-goal').forEach(btn => {
    btn.addEventListener('click', () => {
      const goalId = btn.getAttribute('data-id');
      const goal = goalsData.find(g => g.id === goalId);
      if (goal) openGoalModal(goal, () => render(container));
    });
  });

  container.querySelectorAll('.btn-delete-goal').forEach(btn => {
    btn.addEventListener('click', () => {
      const goalId = btn.getAttribute('data-id');
      const goal = goalsData.find(g => g.id === goalId);
      if (!goal) return;

      openModal({
        title: 'Delete Financial Goal',
        content: `Are you sure you want to delete the goal <strong>"${goal.name}"</strong>? This will remove its SIP contribution from your recommendations.`,
        confirmText: 'Delete Goal',
        confirmClass: 'btn-danger',
        onConfirm: async () => {
          const { error: delErr } = await apiRequest(`/goals/${goalId}`, { method: 'DELETE' });
          if (delErr) {
            showToast({ title: 'Error', message: delErr, type: 'danger' });
            return false;
          }
          showToast({ title: 'Goal Removed', message: `Deleted ${goal.name}`, type: 'success' });
          await render(container);
          return true;
        }
      });
    });
  });
}

/**
 * Open Create or Edit Goal Modal dialog
 */
function openGoalModal(existingGoal, onSaved) {
  const isEdit = !!existingGoal;
  const defaultDate = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const modalForm = document.createElement('form');
  modalForm.id = 'modal-goal-form';
  modalForm.innerHTML = `
    <div class="form-group">
      <label class="form-label" for="goal-name">Goal Name <span class="required">*</span></label>
      <input type="text" id="goal-name" name="name" class="form-input" placeholder="e.g. Retirement Corpus, SUV Car" value="${existingGoal?.name || ''}" required>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="form-group">
        <label class="form-label" for="goal-category">Category</label>
        <select id="goal-category" name="category" class="form-select">
          <option value="Emergency" ${existingGoal?.category === 'Emergency' ? 'selected' : ''}>Emergency Cushion</option>
          <option value="House" ${existingGoal?.category === 'House' ? 'selected' : ''}>House Down Payment</option>
          <option value="Education" ${existingGoal?.category === 'Education' ? 'selected' : ''}>Child Higher Education</option>
          <option value="Vehicle" ${existingGoal?.category === 'Vehicle' ? 'selected' : ''}>Vehicle Purchase</option>
          <option value="Retirement" ${existingGoal?.category === 'Retirement' ? 'selected' : ''}>Retirement Corpus</option>
          <option value="Vacation" ${existingGoal?.category === 'Vacation' ? 'selected' : ''}>Vacation / Travel</option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label" for="goal-priority">Priority</label>
        <select id="goal-priority" name="priority" class="form-select">
          <option value="High" ${existingGoal?.priority === 'High' ? 'selected' : ''}>High Priority</option>
          <option value="Medium" ${(!existingGoal || existingGoal?.priority === 'Medium') ? 'selected' : ''}>Medium Priority</option>
          <option value="Low" ${existingGoal?.priority === 'Low' ? 'selected' : ''}>Low Priority</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="form-group">
        <label class="form-label" for="goal-target">Target Amount (₹) <span class="required">*</span></label>
        <div class="input-group">
          <span class="input-prefix">₹</span>
          <input type="number" id="goal-target" name="targetAmount" class="form-input" placeholder="1000000" min="1000" step="5000" value="${existingGoal?.targetAmount || ''}" required>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="goal-current">Current Savings (₹)</label>
        <div class="input-group">
          <span class="input-prefix">₹</span>
          <input type="number" id="goal-current" name="currentSavings" class="form-input" placeholder="100000" min="0" step="5000" value="${existingGoal?.currentSavings || '0'}">
        </div>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label" for="goal-date">Target Date <span class="required">*</span></label>
      <input type="date" id="goal-date" name="targetDate" class="form-input" value="${existingGoal?.targetDate || defaultDate}" required>
      <small class="form-hint">Must be a date in the future</small>
    </div>
  `;

  openModal({
    title: isEdit ? 'Edit Financial Goal' : 'Create New Financial Goal',
    content: modalForm,
    confirmText: isEdit ? 'Update Goal' : 'Create Goal',
    confirmClass: 'btn-primary',
    onConfirm: async () => {
      const name = modalForm.elements['name'].value.trim();
      const category = modalForm.elements['category'].value;
      const priority = modalForm.elements['priority'].value;
      const targetAmount = parseFloat(modalForm.elements['targetAmount'].value);
      const currentSavings = parseFloat(modalForm.elements['currentSavings'].value) || 0;
      const targetDate = modalForm.elements['targetDate'].value;

      if (!name) {
        showToast({ title: 'Validation Error', message: 'Goal name is required', type: 'warning' });
        return false;
      }
      if (!targetAmount || targetAmount <= 0) {
        showToast({ title: 'Validation Error', message: 'Target amount must be greater than zero', type: 'warning' });
        return false;
      }
      if (!isFutureDate(targetDate)) {
        showToast({ title: 'Validation Error', message: 'Target date must be in the future', type: 'warning' });
        return false;
      }

      const payload = { name, category, priority, targetAmount, currentSavings, targetDate };

      if (isEdit) {
        const { error: err } = await apiRequest(`/goals/${existingGoal.id}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        if (err) {
          showToast({ title: 'Error', message: err, type: 'danger' });
          return false;
        }
        showToast({ title: 'Goal Updated', message: `Updated "${name}"`, type: 'success' });
      } else {
        const { error: err } = await apiRequest('/goals', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        if (err) {
          showToast({ title: 'Error', message: err, type: 'danger' });
          return false;
        }
        showToast({ title: 'Goal Created', message: `Created "${name}"`, type: 'success' });
      }

      if (onSaved) onSaved();
      return true;
    }
  });
}

export function destroy() {
  goalsData = [];
}
