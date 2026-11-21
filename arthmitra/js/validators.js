/**
 * ArthMitra - Validation & Indian Formatting Helpers
 */

/**
 * Format number as Indian Rupee (₹) with Indian digit grouping (e.g. ₹1,23,456)
 * @param {number} amount - Number to format
 * @param {boolean} compact - Whether to format as Lakhs/Crores (e.g. ₹12.50 L)
 * @returns {string} Formatted currency string
 */
export function formatINR(amount, compact = false) {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0';
  }

  const num = Number(amount);

  if (compact) {
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';
    if (abs >= 10000000) {
      return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
    }
    if (abs >= 100000) {
      return `${sign}₹${(abs / 100000).toFixed(2)} L`;
    }
    if (abs >= 1000) {
      return `${sign}₹${(abs / 1000).toFixed(1)} K`;
    }
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(num);
}

/**
 * Parse an Indian currency string or numeric input to a clean Float
 * @param {string|number} input 
 * @returns {number}
 */
export function parseINR(input) {
  if (typeof input === 'number') return isNaN(input) ? 0 : input;
  if (!input) return 0;
  const cleaned = input.toString().replace(/[^0-9.-]+/g, '');
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Check if email format is valid
 * @param {string} email 
 * @returns {boolean}
 */
export function isValidEmail(email) {
  const re = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
  return re.test(String(email).toLowerCase().trim());
}

/**
 * Evaluate password strength (0 to 4 score)
 * Rule: ≥8 chars, 1 number, 1 special symbol
 * @param {string} password 
 * @returns {{ score: number, label: string, color: string, className: string }}
 */
export function evaluatePasswordStrength(password) {
  if (!password) {
    return { score: 0, label: '', color: 'transparent', className: '' };
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  switch (score) {
    case 1:
      return { score: 1, label: 'Weak', color: '#EF4444', className: 'strength-weak' };
    case 2:
      return { score: 2, label: 'Fair', color: '#F59E0B', className: 'strength-fair' };
    case 3:
      return { score: 3, label: 'Good', color: '#0284C7', className: 'strength-good' };
    case 4:
      return { score: 4, label: 'Strong', color: '#10B981', className: 'strength-strong' };
    default:
      return { score: 0, label: 'Very Weak', color: '#EF4444', className: 'strength-weak' };
  }
}

/**
 * Check password requirements: ≥8 chars with at least one number and one symbol
 * @param {string} password 
 * @returns {boolean}
 */
export function isValidPassword(password) {
  if (!password || password.length < 8) return false;
  const hasNumber = /[0-9]/.test(password);
  const hasSymbol = /[^a-zA-Z0-9]/.test(password);
  return hasNumber && hasSymbol;
}

/**
 * Check if a date string is in the future
 * @param {string} dateString (YYYY-MM-DD)
 * @returns {boolean}
 */
export function isFutureDate(dateString) {
  if (!dateString) return false;
  const target = new Date(dateString);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return target > today;
}

/**
 * Display inline validation error on field with ARIA bindings
 * @param {HTMLElement} inputElement 
 * @param {string|null} errorMessage 
 */
export function setFieldError(inputElement, errorMessage) {
  if (!inputElement) return;

  const errorId = `${inputElement.id || inputElement.name}-error`;
  let errorEl = document.getElementById(errorId);

  if (errorMessage) {
    inputElement.setAttribute('aria-invalid', 'true');
    inputElement.setAttribute('aria-describedby', errorId);

    if (!errorEl) {
      errorEl = document.createElement('div');
      errorEl.id = errorId;
      errorEl.className = 'form-error';
      errorEl.setAttribute('role', 'alert');
      inputElement.closest('.form-group')?.appendChild(errorEl);
    }
    errorEl.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span>${errorMessage}</span>
    `;
  } else {
    inputElement.removeAttribute('aria-invalid');
    inputElement.removeAttribute('aria-describedby');
    if (errorEl) {
      errorEl.remove();
    }
  }
}

/**
 * Validate a whole form against a rule set
 * @param {HTMLFormElement} formElement 
 * @param {Object} rules - Map of field name to validation functions
 * @returns {boolean} isValid
 */
export function validateForm(formElement, rules) {
  let isValid = true;
  let firstInvalid = null;

  for (const [fieldName, fieldRules] of Object.entries(rules)) {
    const input = formElement.elements[fieldName];
    if (!input) continue;

    let error = null;
    const value = input.value ? input.value.trim() : '';

    for (const rule of fieldRules) {
      const result = rule(value, formElement);
      if (result !== true) {
        error = result;
        break;
      }
    }

    setFieldError(input, error);
    if (error) {
      isValid = false;
      if (!firstInvalid) firstInvalid = input;
    }
  }

  if (firstInvalid) {
    firstInvalid.focus();
  }

  return isValid;
}
