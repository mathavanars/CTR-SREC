/**
 * ArthMitra - UI Primitives & Global Components
 * Toasts, Modals, Skeletons, Four-State Data Views, SVG Gauge, and XSS Sanitizer
 */

import { icons } from './assets/icons.js';

/**
 * XSS Sanitizer - Safely escape HTML characters
 * @param {string} str 
 * @returns {string} escaped string
 */
export function sanitizeHTML(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

/**
 * Global Toast System
 * @param {Object} options 
 * @param {string} options.title
 * @param {string} options.message
 * @param {'success'|'danger'|'warning'|'info'} options.type
 * @param {number} options.duration
 */
export function showToast({ title = '', message = '', type = 'info', duration = 4000 }) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'status');

  let iconSvg = icons.info(20);
  if (type === 'success') iconSvg = icons.check(20);
  if (type === 'danger') iconSvg = icons.alertCircle(20);
  if (type === 'warning') iconSvg = icons.alertCircle(20);

  toast.innerHTML = `
    <div class="toast-icon">${iconSvg}</div>
    <div class="toast-content">
      ${title ? `<div class="toast-title">${sanitizeHTML(title)}</div>` : ''}
      <div class="toast-message">${sanitizeHTML(message)}</div>
    </div>
    <button class="toast-close" aria-label="Close notification">
      ${icons.close(16)}
    </button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  const dismiss = () => {
    toast.classList.add('toast-hiding');
    setTimeout(() => toast.remove(), 200);
  };

  closeBtn.addEventListener('click', dismiss);
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
}

/**
 * Global Modal System with Focus Trap and ARIA bindings
 */
let activeModalBackdrop = null;
let previousActiveElement = null;

export function openModal({
  title = '',
  content = '',
  size = 'md',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmClass = 'btn-primary',
  showCancel = true,
  onConfirm = null,
  onCancel = null
}) {
  closeModal();

  previousActiveElement = document.activeElement;

  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.setAttribute('role', 'presentation');

  const dialog = document.createElement('div');
  dialog.className = `modal-dialog ${size === 'lg' ? 'modal-dialog-lg' : ''}`;
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');
  dialog.setAttribute('aria-labelledby', 'modal-dialog-title');

  dialog.innerHTML = `
    <div class="modal-header">
      <h2 id="modal-dialog-title" class="modal-title">${sanitizeHTML(title)}</h2>
      <button class="btn-icon modal-close-btn" aria-label="Close dialog">
        ${icons.close(20)}
      </button>
    </div>
    <div class="modal-body">
      ${typeof content === 'string' ? content : ''}
    </div>
    <div class="modal-footer">
      ${showCancel ? `<button type="button" class="btn btn-secondary modal-cancel-btn">${sanitizeHTML(cancelText)}</button>` : ''}
      ${confirmText ? `<button type="button" class="btn ${confirmClass} modal-confirm-btn">${sanitizeHTML(confirmText)}</button>` : ''}
    </div>
  `;

  if (typeof content !== 'string' && content instanceof HTMLElement) {
    dialog.querySelector('.modal-body').appendChild(content);
  }

  backdrop.appendChild(dialog);
  document.body.appendChild(backdrop);
  document.body.style.overflow = 'hidden';
  activeModalBackdrop = backdrop;

  // Event handlers
  const closeBtn = dialog.querySelector('.modal-close-btn');
  const cancelBtn = dialog.querySelector('.modal-cancel-btn');
  const confirmBtn = dialog.querySelector('.modal-confirm-btn');

  const handleClose = () => {
    if (onCancel) onCancel();
    closeModal();
  };

  closeBtn?.addEventListener('click', handleClose);
  cancelBtn?.addEventListener('click', handleClose);

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) handleClose();
  });

  confirmBtn?.addEventListener('click', async () => {
    if (onConfirm) {
      confirmBtn.classList.add('btn-loading');
      try {
        const shouldClose = await onConfirm();
        if (shouldClose !== false) {
          closeModal();
        }
      } catch (err) {
        console.error('Modal confirm action error:', err);
      } finally {
        confirmBtn.classList.remove('btn-loading');
      }
    } else {
      closeModal();
    }
  });

  // Focus trap
  const focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusable.length > 0) {
    focusable[0].focus();
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleClose();
    } else if (e.key === 'Tab') {
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        last.focus();
        e.preventDefault();
      } else if (!e.shiftKey && document.activeElement === last) {
        first.focus();
        e.preventDefault();
      }
    }
  };

  backdrop._handleKeyDown = handleKeyDown;
  document.addEventListener('keydown', handleKeyDown);

  return { backdrop, dialog };
}

export function closeModal() {
  if (activeModalBackdrop) {
    if (activeModalBackdrop._handleKeyDown) {
      document.removeEventListener('keydown', activeModalBackdrop._handleKeyDown);
    }
    activeModalBackdrop.remove();
    activeModalBackdrop = null;
    document.body.style.overflow = '';
    if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
      previousActiveElement.focus();
    }
  }
}

/**
 * Semicircle SVG Gauge for Financial Health Score (0-100)
 * Color thresholds: <40 Red, 40-70 Amber, >70 Green
 * @param {number} score 
 * @param {string} label 
 * @returns {string} SVG HTML
 */
export function renderFinancialHealthGauge(score = 72, label = 'Health Score') {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  const radius = 80;
  const circumference = Math.PI * radius; // Half circle
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  let strokeColor = '#10B981'; // Green
  let categoryText = 'Excellent';
  let badgeClass = 'badge-success';

  if (clampedScore < 40) {
    strokeColor = '#EF4444'; // Red
    categoryText = 'Needs Attention';
    badgeClass = 'badge-danger';
  } else if (clampedScore <= 70) {
    strokeColor = '#F59E0B'; // Amber
    categoryText = 'Fair / Improving';
    badgeClass = 'badge-warning';
  }

  return `
    <div class="gauge-container" role="meter" aria-valuenow="${clampedScore}" aria-valuemin="0" aria-valuemax="100" aria-label="Financial Health Score ${clampedScore} out of 100">
      <svg class="gauge-svg" viewBox="0 0 200 125" aria-hidden="true">
        <!-- Background Track -->
        <path class="gauge-arc-bg" d="M 20 110 A 80 80 0 0 1 180 110" />
        <!-- Filled Progress Arc -->
        <path class="gauge-arc-fill"
          d="M 20 110 A 80 80 0 0 1 180 110"
          stroke="${strokeColor}"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${strokeDashoffset}"
        />
        <!-- Center Value -->
        <text class="gauge-score-text" x="100" y="85">${clampedScore}</text>
        <text class="gauge-label-text" x="100" y="108">/ 100</text>
      </svg>
      <div class="mt-2 text-center">
        <span class="badge ${badgeClass}">${categoryText}</span>
      </div>
    </div>
  `;
}

/**
 * Reusable Stat Card
 */
export function renderStatCard({ label, value, change = null, changeType = 'up', icon = null, subtitle = '' }) {
  const isUp = changeType === 'up';
  const trendClass = isUp ? 'stat-trend-up' : 'stat-trend-down';
  const trendIcon = isUp ? icons.trendingUp(14) : icons.trendingDown(14);

  return `
    <div class="stat-card">
      <div class="stat-header">
        <span class="stat-label">${sanitizeHTML(label)}</span>
        ${icon ? `<div class="stat-icon">${icon}</div>` : ''}
      </div>
      <div class="stat-value tabular-nums">${sanitizeHTML(value)}</div>
      <div class="stat-meta">
        ${change ? `<span class="${trendClass}">${trendIcon} ${sanitizeHTML(change)}</span>` : ''}
        ${subtitle ? `<span class="text-muted">${sanitizeHTML(subtitle)}</span>` : ''}
      </div>
    </div>
  `;
}

/**
 * Reusable Progress Bar
 */
export function renderProgressBar({ current = 0, target = 100, label = '', targetLabel = '', variant = 'primary' }) {
  const percent = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;
  return `
    <div class="progress-bar-container" role="progressbar" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100" aria-label="${sanitizeHTML(label)}">
      ${(label || targetLabel) ? `
        <div class="progress-bar-header">
          <span class="font-medium text-secondary">${sanitizeHTML(label)}</span>
          <span class="text-muted tabular-nums">${sanitizeHTML(targetLabel || `${percent}%`)}</span>
        </div>
      ` : ''}
      <div class="progress-bar-track">
        <div class="progress-bar-fill progress-fill-${variant}" style="width: ${percent}%;"></div>
      </div>
    </div>
  `;
}

/**
 * Four States - Loading Skeletons
 */
export function renderSkeletonCards(count = 4) {
  return Array.from({ length: count }).map(() => `
    <div class="skeleton-card" aria-busy="true" aria-label="Loading content">
      <div class="skeleton skeleton-text skeleton-text-sm" style="width: 40%;"></div>
      <div class="skeleton skeleton-text skeleton-text-lg" style="width: 70%;"></div>
      <div class="skeleton skeleton-text skeleton-text-sm" style="width: 50%;"></div>
    </div>
  `).join('');
}

export function renderSkeletonChart() {
  return `
    <div class="skeleton skeleton-chart" aria-busy="true" aria-label="Loading chart data"></div>
  `;
}

export function renderSkeletonTable(rows = 5, cols = 4) {
  return `
    <div class="skeleton-card" aria-busy="true" aria-label="Loading table">
      ${Array.from({ length: rows }).map(() => `
        <div class="flex gap-4 items-center mb-3">
          ${Array.from({ length: cols }).map(() => `
            <div class="skeleton skeleton-text" style="flex: 1;"></div>
          `).join('')}
        </div>
      `).join('')}
    </div>
  `;
}

/**
 * Four States - Empty State View
 */
export function renderEmptyState({
  icon = icons.info(32),
  title = 'No Data Available',
  description = 'You have not added any items here yet.',
  actionText = '',
  actionId = ''
}) {
  return `
    <div class="state-container">
      <div class="state-icon-wrapper">${icon}</div>
      <h3 class="state-title">${sanitizeHTML(title)}</h3>
      <p class="state-description">${sanitizeHTML(description)}</p>
      ${actionText ? `
        <button type="button" class="btn btn-primary" id="${actionId}">
          ${icons.plus(16)}
          <span>${sanitizeHTML(actionText)}</span>
        </button>
      ` : ''}
    </div>
  `;
}

/**
 * Four States - Error State View
 */
export function renderErrorState({
  title = 'Unable to Load Data',
  message = 'Something went wrong while connecting to the server. Please try again.',
  retryId = 'btn-retry-action'
}) {
  return `
    <div class="state-container">
      <div class="state-icon-wrapper state-icon-error">
        ${icons.alertCircle(32)}
      </div>
      <h3 class="state-title">${sanitizeHTML(title)}</h3>
      <p class="state-description">${sanitizeHTML(message)}</p>
      <button type="button" class="btn btn-outline" id="${retryId}">
        ${icons.refresh(16)}
        <span>Retry</span>
      </button>
    </div>
  `;
}
