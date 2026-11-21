/**
 * api.js
 * Centralized API client for ArthMitra backend.
 */
const API_BASE = '/api/v1';

export const getStoredToken = () => localStorage.getItem('arthmitra_token');
export const setStoredToken = (token) => localStorage.setItem('arthmitra_token', token);
export const removeStoredToken = () => localStorage.removeItem('arthmitra_token');

export const getStoredUser = () => {
  const u = localStorage.getItem('arthmitra_user');
  try {
    return u ? JSON.parse(u) : null;
  } catch {
    return null;
  }
};
export const setStoredUser = (user) => localStorage.setItem('arthmitra_user', JSON.stringify(user));
export const removeStoredUser = () => localStorage.removeItem('arthmitra_user');

async function request(endpoint, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Session expired or invalid
    removeStoredToken();
    removeStoredUser();
  }

  if (!res.ok) {
    let errorDetail = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res;
}

export const api = {
  async register(email, password, full_name) {
    const res = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    });
    return res.json();
  },

  async login(email, password) {
    const res = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    return res.json();
  },

  async getProfile() {
    const res = await request('/profile');
    return res.json();
  },

  async updateProfile(profileData) {
    const res = await request('/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
    return res.json();
  },

  async getPersonas() {
    const res = await request('/personas');
    return res.json();
  },

  async loadPersona(personaId) {
    const res = await request(`/personas/${personaId}/load`, {
      method: 'POST',
    });
    return res.json();
  },

  async getFullAnalysis() {
    const res = await request('/analysis/full');
    return res.json();
  },

  async simulateWhatIf(params) {
    const res = await request('/analysis/whatif', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    return res.json();
  },

  async chat(message, language = 'en') {
    const res = await request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, language }),
    });
    return res.json();
  },

  async downloadReport(format = 'pdf') {
    const token = getStoredToken();
    const res = await fetch(`${API_BASE}/report/download?format=${format}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error('Failed to download report');
    return res.blob();
  },
};
