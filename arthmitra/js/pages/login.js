/**
 * ArthMitra - Login & Registration Page Module
 */

import { apiRequest } from '../api.js';
import { store } from '../store.js';
import { icons } from '../assets/icons.js';
import { showToast } from '../ui.js';
import {
  isValidEmail,
  isValidPassword,
  evaluatePasswordStrength,
  setFieldError,
  validateForm
} from '../validators.js';

let cleanupHandlers = [];

export async function render(container) {
  cleanupHandlers = [];

  container.innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="auth-header">
          <div class="auth-brand-logo">
            ${icons.rupee(28)}
          </div>
          <h1 class="auth-title">ArthMitra</h1>
          <p class="auth-subtitle">AI-Powered Financial Planning for Indian Families</p>
          <button type="button" class="auth-demo-badge" id="btn-fill-demo">
            ${icons.user(14)}
            <span>Fill Demo Credentials (One Click)</span>
          </button>
        </div>

        <!-- Tab Controls -->
        <div class="tabs-nav" role="tablist">
          <button class="tab-btn active flex-1 justify-center" id="tab-login" role="tab" aria-selected="true" aria-controls="pane-login">
            Sign In
          </button>
          <button class="tab-btn flex-1 justify-center" id="tab-register" role="tab" aria-selected="false" aria-controls="pane-register">
            Create Account
          </button>
        </div>

        <div id="auth-alert" class="badge badge-danger mb-4 w-full justify-center" style="display: none; padding: 10px;" role="alert"></div>

        <!-- 1. Sign In Form -->
        <form id="form-login" novalidate>
          <div class="form-group">
            <label class="form-label" for="login-email">
              Email Address <span class="required">*</span>
            </label>
            <input
              type="email"
              id="login-email"
              name="email"
              class="form-input"
              placeholder="rahul.sharma@example.in"
              autocomplete="email"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="login-password">
              Password <span class="required">*</span>
            </label>
            <div class="password-field-wrapper">
              <input
                type="password"
                id="login-password"
                name="password"
                class="form-input"
                placeholder="••••••••"
                autocomplete="current-password"
                required
              />
              <button type="button" class="password-toggle-btn" data-target="login-password" aria-label="Toggle password visibility">
                ${icons.eye(18)}
              </button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary w-full mt-4" id="btn-login-submit" style="width: 100%;">
            Sign In
          </button>
        </form>

        <!-- 2. Register Form -->
        <form id="form-register" style="display: none;" novalidate>
          <div class="form-group">
            <label class="form-label" for="reg-name">
              Full Name <span class="required">*</span>
            </label>
            <input
              type="text"
              id="reg-name"
              name="name"
              class="form-input"
              placeholder="Rahul Sharma"
              autocomplete="name"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-email">
              Email Address <span class="required">*</span>
            </label>
            <input
              type="email"
              id="reg-email"
              name="email"
              class="form-input"
              placeholder="rahul@example.in"
              autocomplete="email"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-password">
              Password <span class="required">*</span>
            </label>
            <div class="password-field-wrapper">
              <input
                type="password"
                id="reg-password"
                name="password"
                class="form-input"
                placeholder="At least 8 chars, 1 number & 1 symbol"
                autocomplete="new-password"
                required
              />
              <button type="button" class="password-toggle-btn" data-target="reg-password" aria-label="Toggle password visibility">
                ${icons.eye(18)}
              </button>
            </div>
            <!-- Password Strength Meter -->
            <div class="password-strength-meter" id="reg-strength-meter">
              <div class="password-strength-seg"></div>
              <div class="password-strength-seg"></div>
              <div class="password-strength-seg"></div>
              <div class="password-strength-seg"></div>
            </div>
            <div class="flex justify-between items-center mt-1">
              <small class="form-hint">At least 8 chars, 1 number, 1 special character</small>
              <small id="reg-strength-text" class="font-medium"></small>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-confirm-password">
              Confirm Password <span class="required">*</span>
            </label>
            <div class="password-field-wrapper">
              <input
                type="password"
                id="reg-confirm-password"
                name="confirmPassword"
                class="form-input"
                placeholder="Re-enter password"
                autocomplete="new-password"
                required
              />
              <button type="button" class="password-toggle-btn" data-target="reg-confirm-password" aria-label="Toggle password visibility">
                ${icons.eye(18)}
              </button>
            </div>
          </div>

          <button type="submit" class="btn btn-primary w-full mt-4" id="btn-reg-submit" style="width: 100%;">
            Create Free Account
          </button>
        </form>
      </div>
    </div>
  `;

  // DOM Elements
  const tabLogin = container.querySelector('#tab-login');
  const tabRegister = container.querySelector('#tab-register');
  const formLogin = container.querySelector('#form-login');
  const formRegister = container.querySelector('#form-register');
  const alertBox = container.querySelector('#auth-alert');
  const fillDemoBtn = container.querySelector('#btn-fill-demo');

  const regPasswordInput = container.querySelector('#reg-password');
  const regStrengthMeter = container.querySelector('#reg-strength-meter');
  const regStrengthText = container.querySelector('#reg-strength-text');

  // Tab switching
  const switchTab = (activeTab) => {
    alertBox.style.display = 'none';
    if (activeTab === 'login') {
      tabLogin.classList.add('active');
      tabLogin.setAttribute('aria-selected', 'true');
      tabRegister.classList.remove('active');
      tabRegister.setAttribute('aria-selected', 'false');
      formLogin.style.display = 'block';
      formRegister.style.display = 'none';
    } else {
      tabRegister.classList.add('active');
      tabRegister.setAttribute('aria-selected', 'true');
      tabLogin.classList.remove('active');
      tabLogin.setAttribute('aria-selected', 'false');
      formRegister.style.display = 'block';
      formLogin.style.display = 'none';
    }
  };

  tabLogin.addEventListener('click', () => switchTab('login'));
  tabRegister.addEventListener('click', () => switchTab('register'));

  // Quick Demo fill
  fillDemoBtn.addEventListener('click', () => {
    switchTab('login');
    formLogin.elements['email'].value = 'rahul.sharma@example.in';
    formLogin.elements['password'].value = 'ArthMitra@2025';
    setFieldError(formLogin.elements['email'], null);
    setFieldError(formLogin.elements['password'], null);
    showToast({ title: 'Demo Credentials Loaded', message: 'Click Sign In to explore.', type: 'info' });
  });

  // Password visibility toggle buttons
  container.querySelectorAll('.password-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = container.querySelector(`#${targetId}`);
      if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = icons.eyeOff(18);
      } else {
        input.type = 'password';
        btn.innerHTML = icons.eye(18);
      }
    });
  });

  // Password strength live updates
  regPasswordInput.addEventListener('input', (e) => {
    const val = e.target.value;
    const strength = evaluatePasswordStrength(val);
    regStrengthMeter.className = `password-strength-meter ${strength.className}`;
    regStrengthText.textContent = strength.label;
    regStrengthText.style.color = strength.color;
  });

  // Inline validation on blur for inputs
  const setupBlurValidation = (form, rules) => {
    Object.keys(rules).forEach(fieldName => {
      const input = form.elements[fieldName];
      if (!input) return;
      input.addEventListener('blur', () => {
        const val = input.value ? input.value.trim() : '';
        for (const rule of rules[fieldName]) {
          const res = rule(val, form);
          if (res !== true) {
            setFieldError(input, res);
            return;
          }
        }
        setFieldError(input, null);
      });
      input.addEventListener('input', () => {
        if (input.getAttribute('aria-invalid') === 'true') {
          setFieldError(input, null);
        }
      });
    });
  };

  // Validation rules
  const loginRules = {
    email: [
      v => !!v || 'Email is required',
      v => isValidEmail(v) || 'Please enter a valid email address'
    ],
    password: [
      v => !!v || 'Password is required'
    ]
  };

  const registerRules = {
    name: [
      v => !!v || 'Name is required',
      v => v.length >= 2 || 'Name must be at least 2 characters'
    ],
    email: [
      v => !!v || 'Email is required',
      v => isValidEmail(v) || 'Please enter a valid email address'
    ],
    password: [
      v => !!v || 'Password is required',
      v => isValidPassword(v) || 'Password must be ≥8 chars with at least 1 number and 1 symbol'
    ],
    confirmPassword: [
      v => !!v || 'Please confirm your password',
      (v, f) => v === f.elements['password'].value || 'Passwords do not match'
    ]
  };

  setupBlurValidation(formLogin, loginRules);
  setupBlurValidation(formRegister, registerRules);

  // Submit Login
  formLogin.addEventListener('submit', async (e) => {
    e.preventDefault();
    alertBox.style.display = 'none';

    if (!validateForm(formLogin, loginRules)) return;

    const submitBtn = container.querySelector('#btn-login-submit');
    submitBtn.classList.add('btn-loading');

    const email = formLogin.elements['email'].value.trim();
    const password = formLogin.elements['password'].value;

    const { data, error } = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    submitBtn.classList.remove('btn-loading');

    if (error) {
      alertBox.textContent = error;
      alertBox.style.display = 'flex';
      return;
    }

    store.setState({
      token: data.token,
      user: data.user
    });

    showToast({ title: 'Welcome to ArthMitra', message: `Signed in as ${data.user.name}`, type: 'success' });

    // Navigate to returnUrl or dashboard
    const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
    const returnUrl = urlParams.get('returnUrl') || 'dashboard';
    window.location.hash = `#${returnUrl}`;
  });

  // Submit Register
  formRegister.addEventListener('submit', async (e) => {
    e.preventDefault();
    alertBox.style.display = 'none';

    if (!validateForm(formRegister, registerRules)) return;

    const submitBtn = container.querySelector('#btn-reg-submit');
    submitBtn.classList.add('btn-loading');

    const name = formRegister.elements['name'].value.trim();
    const email = formRegister.elements['email'].value.trim();
    const password = formRegister.elements['password'].value;

    const { data, error } = await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password })
    });

    submitBtn.classList.remove('btn-loading');

    if (error) {
      alertBox.textContent = error;
      alertBox.style.display = 'flex';
      return;
    }

    store.setState({
      token: data.token,
      user: data.user
    });

    showToast({ title: 'Account Created', message: 'Welcome to ArthMitra!', type: 'success' });
    window.location.hash = '#dashboard';
  });
}

export function destroy() {
  cleanupHandlers.forEach(fn => fn());
  cleanupHandlers = [];
}
