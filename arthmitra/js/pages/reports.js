/**
 * ArthMitra - Reports & Tax Planning Page Module
 * Configurable financial reports, printable executive summary, CSV export, and history list
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { formatINR } from '../validators.js';
import { showToast, renderErrorState, renderSkeletonCards } from '../ui.js';

let reportsList = [];
let selectedReportType = 'Health Diagnostic';
let selectedPeriod = 'FY 2024-25';

export async function render(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="grid grid-cols-3 gap-6">
        ${renderSkeletonCards(3)}
      </div>
      <div class="skeleton-card" style="height: 380px;"></div>
    </div>
  `;

  const { data, error } = await apiRequest('/reports');

  if (error) {
    container.innerHTML = renderErrorState({
      title: 'Failed to load reports',
      message: error,
      retryId: 'btn-retry-reports'
    });
    container.querySelector('#btn-retry-reports')?.addEventListener('click', () => render(container));
    return;
  }

  reportsList = data || [];
  renderReportsView(container);
}

function renderReportsView(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Page Header & Action Controls -->
      <div class="flex justify-between items-center flex-wrap gap-4 no-print">
        <div>
          <h1>Financial Reports & Tax Audit</h1>
          <p class="text-secondary">Generate exportable summaries, printable PDF statements, and tax regime audits</p>
        </div>
        <div class="flex items-center gap-3">
          <button type="button" class="btn btn-outline" id="btn-export-csv">
            ${icons.download(16)}
            <span>Export CSV</span>
          </button>
          <button type="button" class="btn btn-primary" id="btn-print-pdf">
            ${icons.fileText(16)}
            <span>Download PDF</span>
          </button>
        </div>
      </div>

      <!-- Report Generation Configuration Bar -->
      <div class="card no-print">
        <div class="grid grid-cols-3 gap-4 items-end">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sel-report-type">Report Type</label>
            <select id="sel-report-type" class="form-select">
              <option value="Health Diagnostic" ${selectedReportType === 'Health Diagnostic' ? 'selected' : ''}>Comprehensive Financial Health Diagnostic</option>
              <option value="Tax Audit" ${selectedReportType === 'Tax Audit' ? 'selected' : ''}>FY 2024-25 Tax Planning & Deduction Review</option>
              <option value="Net Worth Statement" ${selectedReportType === 'Net Worth Statement' ? 'selected' : ''}>Consolidated Net Worth Statement</option>
              <option value="Debt Payoff" ${selectedReportType === 'Debt Payoff' ? 'selected' : ''}>Debt Amortization & Accelerated Payoff Plan</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" for="sel-report-period">Date Range / Horizon</label>
            <select id="sel-report-period" class="form-select">
              <option value="FY 2024-25" ${selectedPeriod === 'FY 2024-25' ? 'selected' : ''}>Current Financial Year (FY 2024-25)</option>
              <option value="Last 12 Months" ${selectedPeriod === 'Last 12 Months' ? 'selected' : ''}>Trailing 12 Months (TTM)</option>
              <option value="Last Quarter" ${selectedPeriod === 'Last Quarter' ? 'selected' : ''}>Last Quarter (Q3 Oct-Dec)</option>
            </select>
          </div>

          <div>
            <button type="button" class="btn btn-primary w-full" id="btn-generate-report" style="width: 100%;">
              ${icons.refresh(16)}
              <span>Regenerate Report</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Printable Report Preview Sheet -->
      <div class="report-preview-sheet" id="report-canvas">
        
        <!-- Header -->
        <div class="flex justify-between items-start pb-6 mb-6" style="border-bottom: 2px solid var(--border-color);">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <div class="user-avatar-sm" style="background: #2563EB;">${icons.rupee(20)}</div>
              <strong class="text-xl font-bold">ArthMitra Financial Report</strong>
            </div>
            <h2 class="text-lg font-bold" id="rep-display-title">${selectedReportType} – ${selectedPeriod}</h2>
            <p class="text-xs text-muted">Generated for: <strong>Rahul Sharma</strong> (rahul.sharma@example.in) on ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
          </div>
          <div class="text-right">
            <span class="badge badge-success">Verified Advisory</span>
            <div class="text-xs text-muted mt-2">Status: <strong>Finalized</strong></div>
          </div>
        </div>

        <!-- Executive Summary Cards -->
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="p-4 rounded" style="background-color: var(--bg-subtle); border: 1px solid var(--border-color);">
            <small class="text-muted uppercase font-semibold">Total Net Worth</small>
            <div class="text-xl font-bold tabular-nums text-primary mt-1">₹31,75,000</div>
            <small class="text-success">+14.2% YoY</small>
          </div>
          <div class="p-4 rounded" style="background-color: var(--bg-subtle); border: 1px solid var(--border-color);">
            <small class="text-muted uppercase font-semibold">Monthly Surplus</small>
            <div class="text-xl font-bold tabular-nums text-success mt-1">₹29,500</div>
            <small class="text-muted">28.1% Savings Rate</small>
          </div>
          <div class="p-4 rounded" style="background-color: var(--bg-subtle); border: 1px solid var(--border-color);">
            <small class="text-muted uppercase font-semibold">Health Score</small>
            <div class="text-xl font-bold tabular-nums mt-1">74 / 100</div>
            <small class="text-success">Good Financial Health</small>
          </div>
          <div class="p-4 rounded" style="background-color: var(--bg-subtle); border: 1px solid var(--border-color);">
            <small class="text-muted uppercase font-semibold">Debt Obligations</small>
            <div class="text-xl font-bold tabular-nums text-danger mt-1">₹25,45,000</div>
            <small class="text-muted">DTI: 23.8% (Healthy)</small>
          </div>
        </div>

        <!-- Financial Breakdown Table -->
        <h3 class="text-base font-semibold mb-3">Comprehensive Balance & Allocation Breakdown</h3>
        <table class="report-table">
          <thead>
            <tr>
              <th>Instrument / Asset Class</th>
              <th>Category</th>
              <th>Current Balance</th>
              <th>Allocation %</th>
              <th>Tax Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Large & Mid Cap Index Funds</td>
              <td>Equity</td>
              <td class="tabular-nums font-semibold">₹8,50,000</td>
              <td>26.7%</td>
              <td><span class="badge badge-neutral">LTCG (12.5% &gt; ₹1.25L)</span></td>
            </tr>
            <tr>
              <td>Public Provident Fund (PPF)</td>
              <td>Fixed Income</td>
              <td class="tabular-nums font-semibold">₹4,50,000</td>
              <td>14.1%</td>
              <td><span class="badge badge-success">Exempt-Exempt-Exempt (EEE)</span></td>
            </tr>
            <tr>
              <td>National Pension System (NPS)</td>
              <td>Retirement</td>
              <td class="tabular-nums font-semibold">₹2,20,000</td>
              <td>6.9%</td>
              <td><span class="badge badge-primary">Sec 80CCD(1B)</span></td>
            </tr>
            <tr>
              <td>Sovereign Gold Bonds / Digital Gold</td>
              <td>Commodities</td>
              <td class="tabular-nums font-semibold">₹3,00,000</td>
              <td>9.4%</td>
              <td><span class="badge badge-success">Maturity Tax-Free</span></td>
            </tr>
            <tr>
              <td>Bank Fixed Deposits & Savings</td>
              <td>Cash / Emergency</td>
              <td class="tabular-nums font-semibold">₹3,50,000</td>
              <td>11.0%</td>
              <td><span class="badge badge-warning">Taxed at Slab Rates</span></td>
            </tr>
            <tr>
              <td>Primary Residential Property</td>
              <td>Real Estate</td>
              <td class="tabular-nums font-semibold">₹35,00,000</td>
              <td>–</td>
              <td><span class="badge badge-neutral">Sec 24(b) Deduction</span></td>
            </tr>
          </tbody>
        </table>

        <!-- Key Strategic Insights -->
        <div class="p-4 rounded mt-6" style="background-color: var(--bg-subtle); border-left: 4px solid var(--color-primary);">
          <h4 class="font-bold text-primary mb-2">Key Strategic Advisory Notes</h4>
          <ul class="text-xs text-secondary leading-relaxed" style="margin-left: 1.25rem;">
            <li><strong>Section 80C Utilization:</strong> Your PPF and ELSS contributions are on track to fully exhaust the ₹1.5 Lakh ceiling for this financial year.</li>
            <li><strong>NPS Optimization:</strong> Depositing ₹50,000 in NPS Tier 1 unlocks an additional tax refund under Section 80CCD(1B), saving up to ₹15,600 in the 30% slab.</li>
            <li><strong>Loan Prepayment:</strong> Your SBI Home Loan interest rate of 8.5% is moderately low after factoring in tax deductions. Prioritize clearing the remaining ₹3.2L Car Loan first.</li>
          </ul>
        </div>

      </div>

      <!-- Past Reports Archive -->
      <div class="card no-print">
        <div class="card-header">
          <div>
            <h2 class="card-title">${icons.fileText(20)} Historical Generated Reports</h2>
            <p class="card-subtitle">Access previously generated statements and diagnostics</p>
          </div>
        </div>

        <div class="flex flex-col gap-3">
          ${reportsList.map(rep => `
            <div class="flex justify-between items-center p-3 rounded" style="background-color: var(--bg-subtle); border: 1px solid var(--border-color);">
              <div class="flex items-center gap-3">
                <div class="stat-icon" style="width: 36px; height: 36px;">${icons.fileText(18)}</div>
                <div>
                  <strong class="text-sm text-primary block">${rep.title}</strong>
                  <small class="text-muted">Generated: ${rep.date} • Health Score: <strong>${rep.score}</strong></small>
                </div>
              </div>
              <div class="flex gap-2">
                <button type="button" class="btn btn-sm btn-outline btn-view-report" data-title="${rep.title}">
                  View
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

    </div>
  `;

  // Print PDF Trigger
  container.querySelector('#btn-print-pdf')?.addEventListener('click', () => {
    window.print();
  });

  // Export CSV Trigger
  container.querySelector('#btn-export-csv')?.addEventListener('click', () => {
    exportFinancialDataAsCSV();
  });

  // Regenerate Report
  container.querySelector('#btn-generate-report')?.addEventListener('click', async () => {
    selectedReportType = container.querySelector('#sel-report-type').value;
    selectedPeriod = container.querySelector('#sel-report-period').value;

    const btn = container.querySelector('#btn-generate-report');
    btn.classList.add('btn-loading');

    const { data: newRep, error: repErr } = await apiRequest('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ type: selectedReportType, period: selectedPeriod })
    });

    btn.classList.remove('btn-loading');

    if (repErr) {
      showToast({ title: 'Generation Error', message: repErr, type: 'danger' });
      return;
    }

    showToast({ title: 'Report Generated', message: `Compiled ${selectedReportType}`, type: 'success' });
    render(container);
  });
}

/**
 * Generate RFC 4180 CSV export and trigger browser download
 */
function exportFinancialDataAsCSV() {
  const headers = ['Instrument', 'Asset Class', 'Balance (INR)', 'Allocation %', 'Tax Treatment'];
  const rows = [
    ['Nifty 50 Index Mutual Funds', 'Equity', '850000', '26.7', 'LTCG 12.5%'],
    ['Public Provident Fund (PPF)', 'Fixed Income', '450000', '14.1', 'EEE Tax Free'],
    ['National Pension System (NPS)', 'Retirement', '220000', '6.9', 'Sec 80CCD(1B)'],
    ['Sovereign Gold Bonds', 'Commodities', '300000', '9.4', 'Maturity Tax Free'],
    ['Bank Fixed Deposits', 'Cash / Emergency', '350000', '11.0', 'Slab Tax Rate'],
    ['SBI Home Loan Outstanding', 'Liability', '-2200000', '–', 'Sec 24(b) Deduction'],
    ['HDFC Car Loan Outstanding', 'Liability', '-320000', '–', 'Non-Deductible']
  ];

  let csvContent = 'data:text/csv;charset=utf-8,';
  csvContent += headers.map(h => `"${h}"`).join(',') + '\r\n';
  rows.forEach(row => {
    csvContent += row.map(cell => `"${cell}"`).join(',') + '\r\n';
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `ArthMitra_Portfolio_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast({ title: 'CSV Exported', message: 'Financial portfolio downloaded as CSV', type: 'success' });
}

export function destroy() {
  reportsList = [];
}
