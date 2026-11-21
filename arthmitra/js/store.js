/**
 * ArthMitra - Pub/Sub Global State Store
 */

const STORAGE_KEY_TOKEN = 'arthmitra_jwt_token';
const STORAGE_KEY_USER = 'arthmitra_user';
const STORAGE_KEY_SETTINGS = 'arthmitra_settings';

class Store {
  constructor() {
    this.subscribers = new Map();

    // Initial state
    this.state = {
      token: localStorage.getItem(STORAGE_KEY_TOKEN) || null,
      user: this.loadJSON(STORAGE_KEY_USER, null),
      settings: this.loadJSON(STORAGE_KEY_SETTINGS, {
        currency: 'INR',
        formatCompact: false,
        emailNotifications: true,
        sipReminders: true,
        goalAlerts: true
      }),
      profile: null,
      goals: [],
      debts: [],
      unreadNotificationsCount: 3,
      notifications: [
        { id: 1, title: 'SIP Due Tomorrow', message: '₹15,000 for Nifty 50 Index Fund is scheduled for tomorrow.', time: '1h ago', unread: true },
        { id: 2, title: 'Health Score Improved', message: 'Your score moved from 68 to 74 after PPF deposit.', time: '1d ago', unread: true },
        { id: 3, title: 'Tax Saving Reminder', message: 'Invest ₹25,000 more in 80C instruments before March 31.', time: '2d ago', unread: true }
      ]
    };
  }

  loadJSON(key, fallback) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : fallback;
    } catch {
      return fallback;
    }
  }

  getState() {
    return { ...this.state };
  }

  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };

    // Persistent keys sync
    if ('token' in updates) {
      if (updates.token) {
        localStorage.setItem(STORAGE_KEY_TOKEN, updates.token);
      } else {
        localStorage.removeItem(STORAGE_KEY_TOKEN);
      }
    }

    if ('user' in updates) {
      if (updates.user) {
        localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(updates.user));
      } else {
        localStorage.removeItem(STORAGE_KEY_USER);
      }
    }

    if ('settings' in updates) {
      localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(this.state.settings));
    }

    // Notify listeners
    for (const [key, listeners] of this.subscribers.entries()) {
      if (key === '*' || key in updates) {
        listeners.forEach(fn => fn(this.state, prevState));
      }
    }
  }

  /**
   * Subscribe to specific key or all changes ('*')
   * @param {string} key 
   * @param {Function} callback 
   * @returns {Function} unsubscribe
   */
  subscribe(key, callback) {
    if (!this.subscribers.has(key)) {
      this.subscribers.set(key, new Set());
    }
    this.subscribers.get(key).add(callback);

    return () => {
      this.subscribers.get(key)?.delete(callback);
    };
  }

  isAuthenticated() {
    return !!this.state.token;
  }

  clearAuth() {
    this.setState({
      token: null,
      user: null,
      profile: null,
      goals: [],
      debts: []
    });
  }
}

export const store = new Store();
