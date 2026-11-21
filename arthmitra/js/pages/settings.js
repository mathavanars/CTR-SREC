/**
 * ArthMitra - Settings Page Module
 * User preferences, password updates, theme controls, data export & account deletion modal
 */

import { apiRequest } from '../api.js';
import { store } from '../store.js';
import { themeManager } from '../theme.js';
import { icons } from '../assets/icons.js';
import { openModal, showToast } from '../ui.js';
import { isValidPassword } from '../validators.js';

export async function render(container) {
  const user = store.getState().user || {
    name: 'Rahul Sharma',
    email: 'rahul.sharma@example.in',
    phone: '+91 98765 43210'
  };

  const settings = store.getState().settings;
  const currentTheme = themeManager.getTheme();

  container.innerHTML = `
    <div class="flex flex-col gap-6">
      
      <!-- Page Header -->
      <div>
        <h1>Account & Preferences</h1>
        <p class="text-secondary">Manage your user profile, security credentials, display format, and data privacy</p>
      </div>

      <div class="grid grid-cols-2 gap-6">
        
        <!-- 1. Profile Information -->
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.user(20)} Profile Details</h2>
              <p class="card-subtitle">Personal contact and identity details</p>
            </div>
          </div>

          <form id="form-settings-profile">
            <div class="form-group">
              <label class="form-label" for="set-name">Full Name</label>
              <input type="text" id="set-name" class="form-input" value="${user.name}" required>
            </div>

            <div class="form-group">
              <label class="form-label" for="set-email">Email Address</label>
              <input type="email" id="set-email" class="form-input" value="${user.email}" readonly disabled>
              <small class="form-hint">Primary email cannot be modified directly</small>
            </div>

            <div class="form-group">
              <label class="form-label" for="set-phone">Mobile Number (India)</label>
              <input type="tel" id="set-phone" class="form-input" value="${user.phone || '+91 98765 43210'}">
            </div>

            <button type="submit" class="btn btn-primary" id="btn-save-user-profile">
              ${icons.check(16)}
              <span>Save Profile Changes</span>
            </button>
          </form>
        </div>

        <!-- 2. Security & Password -->
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${icons.shield(20)} Security & Password</h2>
              <p class="card-subtitle">Update your master account login credentials</p>
            </div>
          </div>

          <form id="form-settings-password">
            <div class="form-group">
              <label class="form-label" for="set-curr-pass">Current Password</label>
              <input type="password" id="set-curr-pass" class="form-input" placeholder="••••••••" required>
            </div>

            <div class="form-group">
              <label class="form-label" for="set-new-pass">New Password</label>
              <input type="password" id="set-new-pass" class="form-input" placeholder="Min 8 chars, 1 number & 1 symbol" required>
            </div>

            <div class="form-group">
              <label class="form-label" for="set-conf-pass">Confirm New Password</label>
              <input type="password" id="set-conf-pass" class="form-input" placeholder="Re-enter new password" required>
            </div>

            <button type="submit" class="btn btn-secondary" id="btn-update-password">
              ${icons.edit(16)}
              <span>Update Password</span>
            </button>
          </form>
        </div>

      </div>

      <!-- 3. Regional Format & Appearance -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${icons.sun(20)} Appearance & Currency Formatting</h2>
            <p class="card-subtitle">Personalize your color theme and Indian numerical format preferences</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-6">
          <div class="form-group">
            <label class="form-label" for="sel-theme">Color Theme</label>
            <select id="sel-theme" class="form-select">
              <option value="system" ${currentTheme === 'system' ? 'selected' : ''}>Sync with Operating System</option>
              <option value="light" ${currentTheme === 'light' ? 'selected' : ''}>Light Theme</option>
              <option value="dark" ${currentTheme === 'dark' ? 'selected' : ''}>Dark Theme (Slate)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="sel-num-format">Number Notation</label>
            <select id="sel-num-format" class="form-select">
              <option value="indian" selected>Indian Standard (₹ Lakhs & Crores)</option>
              <option value="international">International (₹ Millions & Billions)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 4. Notification Preferences -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${icons.bell(20)} Alert & Advisory Notifications</h2>
            <p class="card-subtitle">Configure email and dashboard notification triggers</p>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <label class="switch">
            <input type="checkbox" id="chk-sip-reminders" ${settings.sipReminders ? 'checked' : ''}>
            <span class="switch-slider"></span>
            <div>
              <strong class="text-sm block">SIP & EMI Due Reminders</strong>
              <small class="text-muted">Receive reminders 48 hours prior to auto-debit dates</small>
            </div>
          </label>

          <label class="switch">
            <input type="checkbox" id="chk-goal-alerts" ${settings.goalAlerts ? 'checked' : ''}>
            <span class="switch-slider"></span>
            <div>
              <strong class="text-sm block">Goal Milestone Celebrations</strong>
              <small class="text-muted">Get notified when savings pass 25%, 50%, and 75% thresholds</small>
            </div>
          </label>

          <label class="switch">
            <input type="checkbox" id="chk-email-notif" ${settings.emailNotifications ? 'checked' : ''}>
            <span class="switch-slider"></span>
            <div>
              <strong class="text-sm block">Monthly Tax & Portfolio Digest</strong>
              <small class="text-muted">Summary of tax deductions utilized and monthly market shifts</small>
            </div>
          </label>
        </div>
      </div>

      <!-- 5. Data Privacy & Danger Zone -->
      <div class="card danger-zone-card">
        <div class="card-header">
          <div>
            <h2 class="card-title text-danger">${icons.trash(20)} Data Privacy & Account Closure</h2>
            <p class="card-subtitle">Export your data backup or permanently erase your account</p>
          </div>
        </div>

        <div class="flex items-center justify-between flex-wrap gap-4">
          <div>
            <strong class="text-sm block">Export Personal Data Backup</strong>
            <small class="text-muted">Download all recorded financial profiles, goals, and simulation histories as JSON</small>
          </div>
          <button type="button" class="btn btn-outline" id="btn-export-json">
            ${icons.download(16)}
            <span>Export JSON Archive</span>
          </button>
        </div>

        <div class="dropdown-divider" style="margin: 1.25rem 0;"></div>

        <div class="flex items-center justify-between flex-wrap gap-4">
          <div>
            <strong class="text-sm text-danger block">Permanently Delete Account</strong>
            <small class="text-muted">Irreversibly delete your profile, goals, calculations, and credentials from ArthMitra</small>
          </div>
          <button type="button" class="btn btn-danger" id="btn-delete-account-modal">
            ${icons.trash(16)}
            <span>Delete Account</span>
          </button>
        </div>
      </div>

    </div>
  `;

  // Profile save
  container.querySelector('#form-settings-profile')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const newName = container.querySelector('#set-name').value.trim();
    const newPhone = container.querySelector('#set-phone').value.trim();

    store.setState({
      user: { ...user, name: newName, phone: newPhone }
    });

    showToast({ title: 'Profile Updated', message: 'User details have been saved', type: 'success' });
  });

  // Password update
  container.querySelector('#form-settings-password')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const curr = container.querySelector('#set-curr-pass').value;
    const next = container.querySelector('#set-new-pass').value;
    const conf = container.querySelector('#set-conf-pass').value;

    if (!curr) {
      showToast({ title: 'Error', message: 'Current password is required', type: 'warning' });
      return;
    }
    if (!isValidPassword(next)) {
      showToast({ title: 'Validation Error', message: 'New password must be ≥8 chars with at least 1 number and 1 symbol', type: 'warning' });
      return;
    }
    if (next !== conf) {
      showToast({ title: 'Error', message: 'New passwords do not match', type: 'warning' });
      return;
    }

    container.querySelector('#form-settings-password').reset();
    showToast({ title: 'Password Changed', message: 'Your password was updated successfully', type: 'success' });
  });

  // Theme changer
  container.querySelector('#sel-theme')?.addEventListener('change', (e) => {
    themeManager.setTheme(e.target.value);
    showToast({ title: 'Theme Updated', message: `Theme set to ${e.target.value}`, type: 'info' });
  });

  // Notification toggles
  ['chk-sip-reminders', 'chk-goal-alerts', 'chk-email-notif'].forEach(id => {
    container.querySelector(`#${id}`)?.addEventListener('change', () => {
      const updatedSettings = {
        sipReminders: container.querySelector('#chk-sip-reminders').checked,
        goalAlerts: container.querySelector('#chk-goal-alerts').checked,
        emailNotifications: container.querySelector('#chk-email-notif').checked
      };
      store.setState({ settings: updatedSettings });
      showToast({ title: 'Preferences Saved', message: 'Notification settings updated', type: 'info' });
    });
  });

  // Export JSON archive
  container.querySelector('#btn-export-json')?.addEventListener('click', () => {
    const dataToExport = {
      user: store.getState().user,
      settings: store.getState().settings,
      exportTimestamp: new Date().toISOString()
    };
    const jsonStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(dataToExport, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', jsonStr);
    dlAnchor.setAttribute('download', `ArthMitra_Backup_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
    showToast({ title: 'Archive Downloaded', message: 'Data backup exported', type: 'success' });
  });

  // Delete account confirmation modal
  container.querySelector('#btn-delete-account-modal')?.addEventListener('click', () => {
    const modalContent = document.createElement('div');
    modalContent.innerHTML = `
      <p class="text-sm text-secondary mb-3">
        This action is <strong>irreversible</strong>. All your financial profiles, goals, loan tracking, and simulation records will be wiped immediately.
      </p>
      <div class="form-group">
        <label class="form-label" for="confirm-delete-input">
          Type <strong>DELETE MY ACCOUNT</strong> to confirm:
        </label>
        <input type="text" id="confirm-delete-input" class="form-input" placeholder="DELETE MY ACCOUNT" autocomplete="off">
      </div>
    `;

    openModal({
      title: 'Confirm Account Deletion',
      content: modalContent,
      confirmText: 'Permanently Delete',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        const typed = modalContent.querySelector('#confirm-delete-input').value.trim();
        if (typed !== 'DELETE MY ACCOUNT') {
          showToast({ title: 'Confirmation Mismatch', message: 'You must type "DELETE MY ACCOUNT" exactly', type: 'warning' });
          return false;
        }

        store.clearAuth();
        localStorage.clear();
        showToast({ title: 'Account Deleted', message: 'Your account data has been completely erased', type: 'info' });
        window.location.hash = '#login';
        return true;
      }
    });
  });
}

export function destroy() {}
