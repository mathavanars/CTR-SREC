/**
 * ArthMitra - Application Bootstrap & Global Event Orchestrator
 */

import { store } from './store.js';
import { themeManager } from './theme.js';
import { router } from './router.js';
import { icons } from './assets/icons.js';
import { showToast } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Global UI Components in Shell
  initShellNavigation();

  // 2. Initialize Router & mount first view
  router.init('app-content-mount');

  // 3. Network status monitoring
  initNetworkListeners();

  // 4. Global keyboard shortcuts
  initKeyboardShortcuts();
});

function initShellNavigation() {
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const hamburgerBtn = document.getElementById('navbar-hamburger');
  const themeToggleBtn = document.getElementById('btn-toggle-theme');
  const notifBtn = document.getElementById('btn-navbar-notifications');
  const notifMenu = document.getElementById('notifications-dropdown-menu');
  const userMenuBtn = document.getElementById('btn-navbar-user');
  const userMenu = document.getElementById('user-dropdown-menu');
  const searchInput = document.getElementById('navbar-search-input');
  const logoutBtn = document.getElementById('btn-shell-logout');

  // Mobile sidebar drawer open/close
  const toggleMobileSidebar = (open) => {
    if (open) {
      sidebar?.classList.add('mobile-open');
      backdrop?.classList.add('active');
    } else {
      sidebar?.classList.remove('mobile-open');
      backdrop?.classList.remove('active');
    }
  };

  hamburgerBtn?.addEventListener('click', () => toggleMobileSidebar(true));
  backdrop?.addEventListener('click', () => toggleMobileSidebar(false));

  // Close mobile sidebar on any nav click
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 640) toggleMobileSidebar(false);
    });
  });

  // Dark/Light Theme Toggle
  const updateThemeIcon = (theme) => {
    if (themeToggleBtn) {
      themeToggleBtn.innerHTML = theme === 'dark' ? icons.sun(18) : icons.moon(18);
      themeToggleBtn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`);
    }
  };

  updateThemeIcon(themeManager.getEffectiveTheme());

  window.addEventListener('themechange', (e) => {
    updateThemeIcon(e.detail.theme);
  });

  themeToggleBtn?.addEventListener('click', () => {
    const next = themeManager.toggleTheme();
    updateThemeIcon(next);
  });

  // Notifications dropdown
  notifBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    userMenu?.classList.remove('show');
    notifMenu?.classList.toggle('show');
  });

  // User menu dropdown
  userMenuBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    notifMenu?.classList.remove('show');
    userMenu?.classList.toggle('show');
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', (e) => {
    if (!notifBtn?.contains(e.target) && !notifMenu?.contains(e.target)) {
      notifMenu?.classList.remove('show');
    }
    if (!userMenuBtn?.contains(e.target) && !userMenu?.contains(e.target)) {
      userMenu?.classList.remove('show');
    }
  });

  // Logout handler
  logoutBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    store.clearAuth();
    userMenu?.classList.remove('show');
    showToast({ title: 'Logged Out', message: 'You have been safely signed out.', type: 'info' });
    window.location.hash = '#login';
  });

  // Global search input handling
  searchInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.toLowerCase().trim();
      searchInput.value = '';
      if (q.includes('goal') || q.includes('target')) window.location.hash = '#goals';
      else if (q.includes('loan') || q.includes('debt') || q.includes('emi')) window.location.hash = '#debts';
      else if (q.includes('invest') || q.includes('sip') || q.includes('mutual') || q.includes('gold')) window.location.hash = '#investments';
      else if (q.includes('chat') || q.includes('coach') || q.includes('ai')) window.location.hash = '#chat';
      else if (q.includes('report') || q.includes('tax') || q.includes('pdf')) window.location.hash = '#reports';
      else if (q.includes('profile') || q.includes('income') || q.includes('expense')) window.location.hash = '#profile';
      else if (q.includes('setting') || q.includes('pass') || q.includes('theme')) window.location.hash = '#settings';
      else window.location.hash = '#dashboard';
    }
  });

  // Sync user info to sidebar & navbar
  const updateUserData = (state) => {
    const user = state.user || { name: 'Rahul Sharma', email: 'rahul.sharma@example.in' };
    const nameEl = document.getElementById('sidebar-user-name');
    const emailEl = document.getElementById('sidebar-user-email');
    const avatarEl = document.getElementById('sidebar-user-avatar');
    const navAvatarEl = document.getElementById('navbar-user-avatar');

    if (nameEl) nameEl.textContent = user.name;
    if (emailEl) emailEl.textContent = user.email;
    const initial = user.name ? user.name.charAt(0).toUpperCase() : 'A';
    if (avatarEl) avatarEl.textContent = initial;
    if (navAvatarEl) navAvatarEl.textContent = initial;
  };

  store.subscribe('user', updateUserData);
  updateUserData(store.getState());
}

function initNetworkListeners() {
  const banner = document.getElementById('offline-banner');
  const updateOnlineStatus = () => {
    if (navigator.onLine) {
      banner?.classList.remove('active');
    } else {
      banner?.classList.add('active');
      showToast({ title: 'Offline Mode', message: 'Internet disconnected. Running in local cache.', type: 'warning' });
    }
  };

  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);
  updateOnlineStatus();
}

function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Focus search on Ctrl+K or Cmd+K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      document.getElementById('navbar-search-input')?.focus();
    }
  });
}
