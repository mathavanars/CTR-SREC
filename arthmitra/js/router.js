/**
 * ArthMitra - Hash-based Client Router & Navigation Controller
 */

import { store } from './store.js';
import { destroyAllCharts } from './charts.js';

// Page modules
import * as LoginPage from './pages/login.js';
import * as DashboardPage from './pages/dashboard.js';
import * as ProfilePage from './pages/profile.js';
import * as GoalsPage from './pages/goals.js';
import * as DebtsPage from './pages/debts.js';
import * as InvestmentsPage from './pages/investments.js';
import * as ChatPage from './pages/chat.js';
import * as ReportsPage from './pages/reports.js';
import * as SettingsPage from './pages/settings.js';
import * as NotFoundPage from './pages/not-found.js';

const routes = {
  'login': { module: LoginPage, title: 'Login & Register', isPublic: true },
  'dashboard': { module: DashboardPage, title: 'Financial Dashboard', isPublic: false },
  'profile': { module: ProfilePage, title: 'Financial Profile', isPublic: false },
  'goals': { module: GoalsPage, title: 'Goal Planning', isPublic: false },
  'debts': { module: DebtsPage, title: 'Debt & Loan Analysis', isPublic: false },
  'investments': { module: InvestmentsPage, title: 'Investment Recommendations', isPublic: false },
  'chat': { module: ChatPage, title: 'AI Financial Coach', isPublic: false },
  'reports': { module: ReportsPage, title: 'Reports & Tax Planning', isPublic: false },
  'settings': { module: SettingsPage, title: 'Account Settings', isPublic: false }
};

class Router {
  constructor() {
    this.currentPage = null;
    this.contentContainer = null;
    this.pageTitleElement = null;
  }

  init(containerId = 'main-content') {
    this.contentContainer = document.getElementById(containerId);
    this.pageTitleElement = document.getElementById('navbar-page-title');

    window.addEventListener('hashchange', () => this.handleRoute());
    this.handleRoute();
  }

  getCurrentRoute() {
    const rawHash = window.location.hash.slice(1) || '';
    const [path] = rawHash.split('?');
    return path.replace(/^\//, '').toLowerCase();
  }

  async handleRoute() {
    let routeKey = this.getCurrentRoute();
    if (!routeKey) {
      routeKey = store.isAuthenticated() ? 'dashboard' : 'login';
      window.location.hash = `#${routeKey}`;
      return;
    }

    const routeConfig = routes[routeKey];

    // Auth Guard check
    const isAuth = store.isAuthenticated();

    if (routeConfig && !routeConfig.isPublic && !isAuth) {
      window.location.hash = `#login?returnUrl=${encodeURIComponent(routeKey)}`;
      return;
    }

    if (routeKey === 'login' && isAuth) {
      window.location.hash = '#dashboard';
      return;
    }

    // Teardown previous page
    if (this.currentPage && typeof this.currentPage.destroy === 'function') {
      try {
        this.currentPage.destroy();
      } catch (e) {
        console.warn('Error during page destroy:', e);
      }
    }
    destroyAllCharts();

    // Toggle app shell elements (hide sidebar/navbar on login page)
    const isAuthView = (routeKey === 'login');
    const sidebar = document.getElementById('app-sidebar');
    const navbar = document.getElementById('app-navbar');
    if (sidebar) sidebar.style.display = isAuthView ? 'none' : '';
    if (navbar) navbar.style.display = isAuthView ? 'none' : '';

    const targetModule = routeConfig ? routeConfig.module : NotFoundPage;
    const pageTitle = routeConfig ? routeConfig.title : 'Page Not Found';

    // Update document title and top navbar title
    document.title = `${pageTitle} – ArthMitra AI`;
    if (this.pageTitleElement && !isAuthView) {
      this.pageTitleElement.textContent = pageTitle;
    }

    // Update active nav links
    this.updateActiveNav(routeKey);

    // Scroll to top
    window.scrollTo(0, 0);

    // Render target page
    if (this.contentContainer) {
      this.contentContainer.innerHTML = '';
      this.currentPage = targetModule;
      try {
        await targetModule.render(this.contentContainer);
      } catch (err) {
        console.error(`Error rendering page ${routeKey}:`, err);
      }
    }
  }

  updateActiveNav(activeKey) {
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
      const href = link.getAttribute('href') || '';
      const linkKey = href.replace(/^#\/?/, '').toLowerCase();
      if (linkKey === activeKey) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    });
  }

  navigate(routeKey) {
    window.location.hash = `#${routeKey}`;
  }
}

export const router = new Router();
