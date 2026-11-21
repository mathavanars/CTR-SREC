/**
 * ArthMitra - Financial Dashboard Page Module
 * Displays health gauge, charts, stat cards, emergency cushion, and top actions
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR } from '../validators.js';
import {
  renderFinancialHealthGauge,
  renderProgressBar,
  renderStatCard,
  renderSkeletonCards,
  renderSkeletonChart,
  renderErrorState,
  renderEmptyState
} from '../ui.js';
import {
  createIncomeExpenseChart,
  createSavingsGrowthChart,
  createGoalProgressChart
} from '../charts.js';

let cleanupHandlers = [];

export async function render(container) {
  cleanupHandlers = [];

  // 1. Initial Loading State (Skeleton Screens)
  container.innerHTML = `
    <div class="flex flex-col gap-6" id="dashboard-content" aria-busy="true">
      <div class="grid grid-cols-4 gap-6">
        ${renderSkeletonCards(4)}
      </div>
      <div class="grid grid-dashboard">
        <div class="col-8">${renderSkeletonChart()}</div>
        <div class="col-4">${renderSkeletonChart()}</div>
      </div>
    </div>
  `;

  // Fetch summary data
  const { data, error } = await apiRequest('/dashboard/summary');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load Dashboard',
      message: error,
      retryId: 'btn-retry-dashboard'
    });
    container.querySelector('#btn-retry-dashboard')?.addEventListener('click', () => {
      render(container);
    });
    return;
  }

  if (!data || (!data.monthlyIncome && !data.netWorth)) {
    container.innerHTML = renderEmptyState({
      icon: icons.dashboard(36),
      title: 'Welcome to ArthMitra!',
      description: 'Start by filling in your financial profile to generate your customized health score and insights.',
      actionText: 'Complete Financial Profile',
      actionId: 'btn-goto-profile'
    });
    container.querySelector('#btn-goto-profile')?.addEventListener('click', () => {
      window.location.hash = '#profile';
    });
    return;
  }

  // 2. Render Success View
  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Top Metrics Row -->
      <div class="grid grid-cols-4 gap-6">
        ${renderStatCard({
          label: 'Estimated Net Worth',
          value: formatINR(data.netWorth),
          change: '+14.2% YoY',
          changeType: 'up',
          icon: icons.wallet(20),
          subtitle: 'Assets minus Liabilities'
        })}
        ${renderStatCard({
          label: 'Monthly Inflow',
          value: formatINR(data.monthlyIncome),
          change: '+5.0% vs Last Qtr',
          changeType: 'up',
          icon: icons.trendingUp(20),
          subtitle: 'Salary, Rental & Other'
        })}
        ${renderStatCard({
          label: 'Monthly Outflow',
          value: formatINR(data.monthlyExpenses),
          change: '-3.2% vs Budget',
          changeType: 'up',
          icon: icons.creditCard(20),
          subtitle: 'Fixed + Variable Expenses'
        })}
        ${renderStatCard({
          label: 'Current Savings Rate',
          value: `${data.savingsRate}%`,
          change: 'Target: > 30%',
          changeType: data.savingsRate >= 25 ? 'up' : 'down',
          icon: icons.target(20),
          subtitle: 'Monthly Inflow Saved'
        })}
      </div>

      <!-- Main Analytical Row -->
      <div class="grid grid-dashboard">
        
        <!-- Income vs Expense Bar Chart -->
        <div class="col-8">
          <div class="card h-full">
            <div class="card-header">
              <div>
                <h2 class="card-title">${icons.trendingUp(20)} Inflow vs Outflow Trend</h2>
                <p class="card-subtitle">Last 12 months financial cash flow</p>
              </div>
              <span class="badge badge-primary">FY 2024-25</span>
            </div>
            <div style="height: 320px; position: relative;">
              <canvas id="chart-income-expense"></canvas>
            </div>
          </div>
        </div>

        <!-- Financial Health Score & Gauge -->
        <div class="col-4">
          <div class="card h-full flex flex-col justify-between">
            <div class="card-header">
              <div>
                <h2 class="card-title">${icons.shield(20)} Financial Health Score</h2>
                <p class="card-subtitle">AI-computed holistic stability rating</p>
              </div>
            </div>

            <!-- Animated SVG Gauge -->
            ${renderFinancialHealthGauge(data.healthScore, 'Health Rating')}

            <!-- Factors Breakdown -->
            <div class="health-factors-list">
              <div class="health-factor-item">
                <span class="text-secondary">Savings Ratio</span>
                <span class="font-semibold text-success">${data.healthFactors.savingsRate.status}</span>
              </div>
              <div class="health-factor-item">
                <span class="text-secondary">Emergency Cushion</span>
                <span class="font-semibold text-warning">${data.healthFactors.emergencyCushion.status}</span>
              </div>
              <div class="health-factor-item">
                <span class="text-secondary">Debt-to-Income</span>
                <span class="font-semibold text-success">${data.healthFactors.debtToIncome.status}</span>
              </div>
              <div class="health-factor-item">
                <span class="text-secondary">Insurance Cover</span>
                <span class="font-semibold text-primary">${data.healthFactors.insuranceCoverage.status}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Secondary Row: Wealth Growth, Emergency Cushion, and Top Actions -->
      <div class="grid grid-dashboard">

        <!-- Wealth Accumulation Line Chart -->
        <div class="col-6">
          <div class="card h-full">
            <div class="card-header">
              <div>
                <h2 class="card-title">${icons.layers(20)} Net Worth Growth Trajectory</h2>
                <p class="card-subtitle">5-Year multi-asset compounding history</p>
              </div>
            </div>
            <div style="height: 280px; position: relative;">
              <canvas id="chart-wealth-growth"></canvas>
            </div>
          </div>
        </div>

        <!-- Emergency Fund & Top 3 Actions -->
        <div class="col-6 flex flex-col gap-6">
          
          <!-- Emergency Fund Widget -->
          <div class="card card-gradient-primary">
            <div class="card-header">
              <div>
                <h2 class="card-title">${icons.shield(20)} Emergency Fund Cushion</h2>
                <p class="card-subtitle">Recommended minimum: 6 months of living expenses</p>
              </div>
              <span class="badge ${data.emergencyFund.monthsCovered >= 5 ? 'badge-success' : 'badge-warning'}">
                ${data.emergencyFund.monthsCovered} / 6.0 Months
              </span>
            </div>

            ${renderProgressBar({
              current: data.emergencyFund.current,
              target: data.emergencyFund.target,
              label: `${formatINR(data.emergencyFund.current)} Saved`,
              targetLabel: `Target: ${formatINR(data.emergencyFund.target)}`,
              variant: data.emergencyFund.monthsCovered >= 5 ? 'success' : 'warning'
            })}

            <div class="flex justify-between items-center mt-3 text-xs text-muted">
              <span>Current monthly expense: ${formatINR(data.monthlyExpenses)}</span>
              <span>Shortfall: ${formatINR(Math.max(0, data.emergencyFund.target - data.emergencyFund.current))}</span>
            </div>
          </div>

          <!-- Top 3 Priority Actions -->
          <div class="card">
            <div class="card-header">
              <div>
                <h2 class="card-title">${icons.target(20)} Top 3 Priority Actions This Month</h2>
                <p class="card-subtitle">Personalized high-leverage steps to boost your score</p>
              </div>
            </div>

            <div class="dashboard-actions-list">
              ${data.topActions.map(action => `
                <div class="action-card">
                  <div class="action-content">
                    <div class="flex items-center gap-2">
                      <span class="action-title">${action.title}</span>
                      <span class="badge badge-${action.impactType}">${action.impact}</span>
                    </div>
                    <span class="action-desc">${action.desc}</span>
                  </div>
                  <button type="button" class="btn btn-sm btn-outline action-cta-btn" data-target="${action.action}">
                    Action
                    ${icons.arrowRight(14)}
                  </button>
                </div>
              `).join('')}
            </div>
          </div>

        </div>

      </div>

    </div>
  `;

  // Attach action button event listeners
  container.querySelectorAll('.action-cta-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetHash = btn.getAttribute('data-target');
      if (targetHash) window.location.hash = targetHash;
    });
  });

  // Render Chart.js charts
  const canvasIncome = container.querySelector('#chart-income-expense');
  if (canvasIncome) {
    createIncomeExpenseChart(canvasIncome, data.monthlyTrends);
  }

  const canvasWealth = container.querySelector('#chart-wealth-growth');
  if (canvasWealth) {
    createSavingsGrowthChart(canvasWealth, data.wealthGrowth);
  }
}

export function destroy() {
  cleanupHandlers.forEach(fn => fn());
  cleanupHandlers = [];
}
