/**
 * ArthMitra - Investment Recommendations & Multi-Asset Growth Simulator
 * Asset allocation cards, rationale, and interactive Chart.js comparison of FD vs SIP vs Gold
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR } from '../validators.js';
import { renderErrorState, renderSkeletonCards } from '../ui.js';
import { createInstrumentComparisonChart } from '../charts.js';

let compParams = {
  monthlyInvestment: 15000,
  years: 15,
  fdRate: 7.0,
  sipRate: 12.5,
  goldRate: 10.0
};

export async function render(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="grid grid-cols-3 gap-6">
        ${renderSkeletonCards(3)}
      </div>
      <div class="skeleton-card" style="height: 350px;"></div>
    </div>
  `;

  const { data, error } = await apiRequest('/investments/recommendations');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load recommendations',
      message: error,
      retryId: 'btn-retry-investments'
    });
    container.querySelector('#btn-retry-investments')?.addEventListener('click', () => render(container));
    return;
  }

  const { riskAppetite, allocations } = data;

  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Page Header -->
      <div class="flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1>Tailored Investment Blueprint</h1>
          <p class="text-secondary">AI asset allocation aligned with your <strong>${riskAppetite}</strong> risk appetite and Indian tax-advantaged instruments</p>
        </div>
        <div class="badge badge-primary" style="padding: 6px 12px; font-size: 0.8125rem;">
          Risk Profile: ${riskAppetite}
        </div>
      </div>

      <!-- Asset Allocation Percentage Visual Bar -->
      <div class="card card-gradient-primary">
        <h3 class="text-sm font-semibold uppercase text-muted mb-3">Target Portfolio Allocation</h3>
        <div class="progress-bar-track" style="height: 14px; display: flex; overflow: hidden; border-radius: var(--radius-full);">
          ${allocations.map((a, i) => {
            const colors = ['#2563EB', '#10B981', '#D97706', '#8B5CF6', '#0D9488'];
            const bg = colors[i % colors.length];
            return `<div style="width: ${a.percentage}%; background-color: ${bg}; height: 100%;" title="${a.instrument}: ${a.percentage}%"></div>`;
          }).join('')}
        </div>
        <div class="flex flex-wrap gap-4 mt-3 text-xs">
          ${allocations.map((a, i) => {
            const colors = ['#2563EB', '#10B981', '#D97706', '#8B5CF6', '#0D9488'];
            const bg = colors[i % colors.length];
            return `
              <div class="flex items-center gap-1">
                <span style="width: 10px; height: 10px; border-radius: 50%; background-color: ${bg}; display: inline-block;"></span>
                <span>${a.category}: <strong>${a.percentage}%</strong></span>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- Recommendation Cards Grid -->
      <div class="grid grid-cols-2 gap-6">
        ${allocations.map(item => {
          let riskBadgeClass = 'badge-danger';
          if (item.risk === 'Low') riskBadgeClass = 'badge-success';
          if (item.risk === 'Moderate') riskBadgeClass = 'badge-warning';

          return `
            <div class="recommendation-card">
              <div class="recommendation-header">
                <div>
                  <span class="badge badge-neutral">${item.category}</span>
                  <h3 class="text-base font-bold text-primary mt-1">${item.instrument}</h3>
                </div>
                <div class="text-right">
                  <div class="text-xl font-bold text-primary tabular-nums">${item.percentage}%</div>
                  <small class="text-muted">Target Share</small>
                </div>
              </div>

              <div class="flex items-center justify-between text-xs py-2 px-3 rounded" style="background-color: var(--bg-subtle);">
                <span>Expected CAGR: <strong class="text-success">${item.expectedReturn}</strong></span>
                <span class="badge ${riskBadgeClass}">${item.risk} Risk</span>
              </div>

              <div class="text-xs text-secondary leading-relaxed">
                <strong class="text-primary block mb-1">Financial Rationale:</strong>
                ${item.rationale}
              </div>

              <div class="text-xs p-3 rounded" style="background-color: var(--color-primary-subtle); border-left: 3px solid var(--color-primary);">
                <strong class="text-primary block mb-1">Why this for you?</strong>
                ${item.whyForYou}
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <!-- Interactive Comparison Chart: FD vs SIP vs Gold -->
      <div class="card">
        <div class="card-header flex-wrap">
          <div>
            <h2 class="card-title">${icons.trendingUp(20)} Wealth Multiplier: FD vs Mutual Fund SIP vs Gold</h2>
            <p class="card-subtitle">Simulate real compound returns over long-term Indian investment horizons</p>
          </div>
          <span class="badge badge-success">Interactive Simulator</span>
        </div>

        <!-- Controls Row -->
        <div class="grid grid-cols-4 gap-4 mb-6 p-4 rounded" style="background-color: var(--bg-subtle);">
          
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sim-amount">Monthly Investment</label>
            <div class="input-group">
              <span class="input-prefix">₹</span>
              <input type="number" id="sim-amount" class="form-input" value="${compParams.monthlyInvestment}" step="1000" min="1000">
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sim-years">Horizon (Years: <span id="lbl-sim-years">${compParams.years}</span>)</label>
            <input type="range" id="sim-years" min="1" max="30" value="${compParams.years}" class="form-input" style="padding: 0; cursor: pointer;">
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sim-sip-rate">Equity SIP Return (%)</label>
            <div class="input-group">
              <input type="number" id="sim-sip-rate" class="form-input" value="${compParams.sipRate}" step="0.5" min="1" max="25">
              <span class="input-suffix">%</span>
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sim-fd-rate">FD Rate (%)</label>
            <div class="input-group">
              <input type="number" id="sim-fd-rate" class="form-input" value="${compParams.fdRate}" step="0.25" min="1" max="15">
              <span class="input-suffix">%</span>
            </div>
          </div>

        </div>

        <!-- Canvas Container -->
        <div style="height: 360px; position: relative;">
          <canvas id="chart-instruments-comparison"></canvas>
        </div>
      </div>

      <!-- SEBI Educational Disclaimer -->
      <div class="disclaimer-box" role="note">
        <div style="flex-shrink: 0; color: var(--color-warning);">${icons.alertCircle(24)}</div>
        <div>
          <strong class="block text-primary mb-1">Regulatory & Statutory Disclaimer</strong>
          ArthMitra is an AI-powered financial educational and planning tool designed to illustrate personal finance principles, budgeting, and compound interest models. This platform does not provide SEBI-registered investment advice or guarantee any specific portfolio returns. Mutual fund investments are subject to market risks; please read all scheme-related documents carefully and consult a qualified SEBI-registered investment adviser (RIA) before committing funds.
        </div>
      </div>

    </div>
  `;

  // Simulator Inputs Event Handlers
  const canvas = container.querySelector('#chart-instruments-comparison');
  const simAmount = container.querySelector('#sim-amount');
  const simYears = container.querySelector('#sim-years');
  const lblYears = container.querySelector('#lbl-sim-years');
  const simSipRate = container.querySelector('#sim-sip-rate');
  const simFdRate = container.querySelector('#sim-fd-rate');

  const updateChart = () => {
    compParams.monthlyInvestment = parseFloat(simAmount.value) || 10000;
    compParams.years = parseInt(simYears.value, 10) || 15;
    compParams.sipRate = parseFloat(simSipRate.value) || 12.0;
    compParams.fdRate = parseFloat(simFdRate.value) || 7.0;
    lblYears.textContent = compParams.years;

    createInstrumentComparisonChart(canvas, compParams);
  };

  simAmount?.addEventListener('input', updateChart);
  simYears?.addEventListener('input', updateChart);
  simSipRate?.addEventListener('input', updateChart);
  simFdRate?.addEventListener('input', updateChart);

  // Initial chart render
  if (canvas) {
    createInstrumentComparisonChart(canvas, compParams);
  }
}

export function destroy() {
  // Chart is destroyed via destroyAllCharts in router
}
