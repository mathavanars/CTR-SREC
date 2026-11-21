/**
 * ArthMitra - Chart.js v4 Integration & Factory Functions
 * Theme-aware, Indian Rupee ₹ formatted, accessible, leak-proof
 */

import { formatINR } from './validators.js';

// Chart instance registry for safe destruction on route changes
const activeCharts = new Map();

/**
 * Get current theme colors from computed styles
 */
function getThemeChartColors() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    textColor: isDark ? '#CBD5E1' : '#475569',
    mutedColor: isDark ? '#64748B' : '#94A3B8',
    borderColor: isDark ? '#334155' : '#E2E8F0',
    gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)',
    surfaceBg: isDark ? '#1E293B' : '#FFFFFF',
    primary: '#2563EB',
    primaryHover: '#1D4ED8',
    primarySubtle: 'rgba(37, 99, 235, 0.15)',
    success: '#10B981',
    successSubtle: 'rgba(16, 185, 129, 0.15)',
    warning: '#F59E0B',
    warningSubtle: 'rgba(245, 158, 11, 0.15)',
    danger: '#EF4444',
    gold: '#D97706',
    goldSubtle: 'rgba(217, 119, 6, 0.15)',
    equity: '#8B5CF6'
  };
}

/**
 * Destroy a specific chart instance by canvas ID
 * @param {string} chartId 
 */
export function destroyChart(chartId) {
  if (activeCharts.has(chartId)) {
    try {
      activeCharts.get(chartId).destroy();
    } catch (e) {
      console.warn(`Error destroying chart ${chartId}:`, e);
    }
    activeCharts.delete(chartId);
  }
}

/**
 * Destroy all registered chart instances (called on route transitions)
 */
export function destroyAllCharts() {
  for (const [id, chart] of activeCharts.entries()) {
    try {
      chart.destroy();
    } catch (e) {
      console.warn(`Error destroying chart ${id}:`, e);
    }
  }
  activeCharts.clear();
}

/**
 * Update chart theme colors dynamically on dark/light switch
 */
export function updateAllChartsTheme() {
  const colors = getThemeChartColors();
  for (const chart of activeCharts.values()) {
    if (chart.options.scales) {
      if (chart.options.scales.x) {
        chart.options.scales.x.ticks.color = colors.textColor;
        chart.options.scales.x.grid.color = colors.gridColor;
        chart.options.scales.x.grid.borderColor = colors.borderColor;
      }
      if (chart.options.scales.y) {
        chart.options.scales.y.ticks.color = colors.textColor;
        chart.options.scales.y.grid.color = colors.gridColor;
        chart.options.scales.y.grid.borderColor = colors.borderColor;
      }
    }
    if (chart.options.plugins?.legend?.labels) {
      chart.options.plugins.legend.labels.color = colors.textColor;
    }
    chart.update();
  }
}

// Listen to themechange event
window.addEventListener('themechange', () => {
  updateAllChartsTheme();
});

/**
 * 1. Income vs Expense Grouped Bar Chart
 * @param {HTMLCanvasElement} canvas 
 * @param {Object} data 
 * @returns {Chart} instance
 */
export function createIncomeExpenseChart(canvas, data) {
  if (!canvas || !window.Chart) return null;
  const chartId = canvas.id || 'income-expense-chart';
  destroyChart(chartId);

  const colors = getThemeChartColors();
  const months = data.months || ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
  const income = data.income || [75000, 75000, 78000, 78000, 80000, 82000, 95000, 85000, 85000, 88000, 88000, 92000];
  const expense = data.expense || [48000, 51000, 46000, 52000, 54000, 49000, 68000, 53000, 51000, 50000, 49000, 53000];

  canvas.setAttribute('aria-label', `Income vs Expense chart over last ${months.length} months`);

  const chart = new window.Chart(canvas, {
    type: 'bar',
    data: {
      labels: months,
      datasets: [
        {
          label: 'Monthly Income',
          data: income,
          backgroundColor: colors.primary,
          borderRadius: 6,
          barPercentage: 0.7,
          categoryPercentage: 0.8
        },
        {
          label: 'Monthly Expense',
          data: expense,
          backgroundColor: colors.danger,
          borderRadius: 6,
          barPercentage: 0.7,
          categoryPercentage: 0.8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: {
            color: colors.textColor,
            usePointStyle: true,
            boxWidth: 8,
            font: { family: 'Inter', size: 12 }
          }
        },
        tooltip: {
          backgroundColor: colors.surfaceBg,
          titleColor: colors.textColor,
          bodyColor: colors.textColor,
          borderColor: colors.borderColor,
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${formatINR(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: colors.textColor, font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.textColor,
            font: { family: 'Inter', size: 11 },
            callback: (val) => formatINR(val, true)
          }
        }
      }
    }
  });

  activeCharts.set(chartId, chart);
  return chart;
}

/**
 * 2. Savings & Wealth Growth Line Chart with Area Fill
 * @param {HTMLCanvasElement} canvas 
 * @param {Object} data 
 * @returns {Chart} instance
 */
export function createSavingsGrowthChart(canvas, data) {
  if (!canvas || !window.Chart) return null;
  const chartId = canvas.id || 'savings-growth-chart';
  destroyChart(chartId);

  const colors = getThemeChartColors();
  const labels = data.labels || ['2020', '2021', '2022', '2023', '2024', '2025'];
  const values = data.values || [250000, 520000, 890000, 1420000, 2150000, 3100000];

  canvas.setAttribute('aria-label', `Wealth accumulation trend from ${labels[0]} to ${labels[labels.length - 1]}`);

  const chart = new window.Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Total Net Savings (₹)',
          data: values,
          borderColor: colors.success,
          backgroundColor: colors.successSubtle,
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointBackgroundColor: colors.success,
          pointBorderColor: '#FFFFFF',
          pointHoverRadius: 6,
          pointRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: colors.surfaceBg,
          titleColor: colors.textColor,
          bodyColor: colors.textColor,
          borderColor: colors.borderColor,
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => `Net Wealth: ${formatINR(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: colors.textColor, font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.textColor,
            font: { family: 'Inter', size: 11 },
            callback: (val) => formatINR(val, true)
          }
        }
      }
    }
  });

  activeCharts.set(chartId, chart);
  return chart;
}

/**
 * 3. Goal Progress Doughnut Chart
 * @param {HTMLCanvasElement} canvas 
 * @param {Array} goals 
 * @returns {Chart} instance
 */
export function createGoalProgressChart(canvas, goals = []) {
  if (!canvas || !window.Chart) return null;
  const chartId = canvas.id || 'goals-progress-chart';
  destroyChart(chartId);

  const colors = getThemeChartColors();
  const defaultGoals = [
    { name: 'Emergency Fund', current: 300000, target: 450000 },
    { name: 'Home Down Payment', current: 850000, target: 1500000 },
    { name: 'Child Education', current: 420000, target: 1200000 },
    { name: 'New Car', current: 350000, target: 600000 }
  ];

  const items = (goals && goals.length > 0) ? goals : defaultGoals;
  const labels = items.map(g => g.name);
  const data = items.map(g => g.current);
  const palette = [colors.primary, colors.success, colors.warning, colors.equity, colors.gold];

  canvas.setAttribute('aria-label', `Goal progress breakdown among ${items.length} active goals`);

  const chart = new window.Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: palette.slice(0, items.length),
          borderWidth: 2,
          borderColor: colors.surfaceBg,
          hoverOffset: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: colors.textColor,
            usePointStyle: true,
            boxWidth: 8,
            font: { family: 'Inter', size: 12 }
          }
        },
        tooltip: {
          backgroundColor: colors.surfaceBg,
          titleColor: colors.textColor,
          bodyColor: colors.textColor,
          borderColor: colors.borderColor,
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => {
              const item = items[ctx.dataIndex];
              const pct = Math.round((item.current / item.target) * 100);
              return `${ctx.label}: ${formatINR(ctx.parsed)} of ${formatINR(item.target)} (${pct}%)`;
            }
          }
        }
      }
    }
  });

  activeCharts.set(chartId, chart);
  return chart;
}

/**
 * 4. FD vs SIP vs Gold Projected Growth Comparison Line Chart
 * @param {HTMLCanvasElement} canvas 
 * @param {Object} params - { monthlyInvestment, years, fdRate, sipRate, goldRate }
 * @returns {Chart} instance
 */
export function createInstrumentComparisonChart(canvas, params = {}) {
  if (!canvas || !window.Chart) return null;
  const chartId = canvas.id || 'instrument-comparison-chart';
  destroyChart(chartId);

  const colors = getThemeChartColors();
  const P = params.monthlyInvestment || 10000;
  const years = params.years || 15;
  const fdRate = (params.fdRate ?? 7.0) / 100;
  const sipRate = (params.sipRate ?? 12.5) / 100;
  const goldRate = (params.goldRate ?? 10.0) / 100;

  const labels = [];
  const fdValues = [];
  const sipValues = [];
  const goldValues = [];
  const investedValues = [];

  // Monthly compounding SIP formula for each year
  for (let y = 1; y <= years; y++) {
    labels.push(`Year ${y}`);
    const n = y * 12;
    investedValues.push(P * n);

    // Monthly rate
    const rFD = fdRate / 12;
    const rSIP = sipRate / 12;
    const rGold = goldRate / 12;

    const fvFD = P * ((Math.pow(1 + rFD, n) - 1) / rFD) * (1 + rFD);
    const fvSIP = P * ((Math.pow(1 + rSIP, n) - 1) / rSIP) * (1 + rSIP);
    const fvGold = P * ((Math.pow(1 + rGold, n) - 1) / rGold) * (1 + rGold);

    fdValues.push(Math.round(fvFD));
    sipValues.push(Math.round(fvSIP));
    goldValues.push(Math.round(fvGold));
  }

  canvas.setAttribute('aria-label', `Projected comparison of FD, Equity SIP, and Gold over ${years} years`);

  const chart = new window.Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: `Equity SIP (${(sipRate * 100).toFixed(1)}%)`,
          data: sipValues,
          borderColor: colors.primary,
          backgroundColor: colors.primarySubtle,
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 3
        },
        {
          label: `Gold (${(goldRate * 100).toFixed(1)}%)`,
          data: goldValues,
          borderColor: colors.gold,
          backgroundColor: colors.goldSubtle,
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 3
        },
        {
          label: `Fixed Deposit (${(fdRate * 100).toFixed(1)}%)`,
          data: fdValues,
          borderColor: colors.fixedIncome || '#0D9488',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3
        },
        {
          label: 'Total Invested Amount',
          data: investedValues,
          borderColor: colors.mutedColor,
          borderDash: [5, 5],
          borderWidth: 1.5,
          tension: 0,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: colors.textColor,
            usePointStyle: true,
            boxWidth: 8,
            font: { family: 'Inter', size: 12 }
          }
        },
        tooltip: {
          backgroundColor: colors.surfaceBg,
          titleColor: colors.textColor,
          bodyColor: colors.textColor,
          borderColor: colors.borderColor,
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${formatINR(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: colors.textColor, font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.textColor,
            font: { family: 'Inter', size: 11 },
            callback: (val) => formatINR(val, true)
          }
        }
      }
    }
  });

  activeCharts.set(chartId, chart);
  return chart;
}
