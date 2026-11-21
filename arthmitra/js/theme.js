/**
 * ArthMitra - Theme Management (Light / Dark Mode with Persistence & System Sync)
 */

const STORAGE_KEY_THEME = 'arthmitra_theme';

class ThemeManager {
  constructor() {
    this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.currentTheme = localStorage.getItem(STORAGE_KEY_THEME) || 'system';
    
    // Listen for OS system theme changes
    this.mediaQuery.addEventListener('change', () => {
      if (this.currentTheme === 'system') {
        this.applyTheme();
      }
    });

    this.applyTheme();
  }

  getEffectiveTheme() {
    if (this.currentTheme === 'system') {
      return this.mediaQuery.matches ? 'dark' : 'light';
    }
    return this.currentTheme;
  }

  applyTheme() {
    const effective = this.getEffectiveTheme();
    document.documentElement.setAttribute('data-theme', effective);

    // Update meta theme-color for mobile browsers
    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.name = 'theme-color';
      document.head.appendChild(metaThemeColor);
    }
    metaThemeColor.setAttribute('content', effective === 'dark' ? '#0F172A' : '#FFFFFF');

    // Dispatch global event for Chart.js and UI components to re-render
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: effective } }));
  }

  setTheme(theme) {
    if (!['light', 'dark', 'system'].includes(theme)) return;
    this.currentTheme = theme;
    localStorage.setItem(STORAGE_KEY_THEME, theme);
    this.applyTheme();
  }

  toggleTheme() {
    const effective = this.getEffectiveTheme();
    const next = effective === 'dark' ? 'light' : 'dark';
    this.setTheme(next);
    return next;
  }

  getTheme() {
    return this.currentTheme;
  }
}

export const themeManager = new ThemeManager();
