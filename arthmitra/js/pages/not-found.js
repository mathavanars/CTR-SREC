/**
 * ArthMitra - 404 Not Found Page Module
 */

import { icons } from '../assets/icons.js';
import { renderEmptyState } from '../ui.js';

export async function render(container) {
  container.innerHTML = `
    <div class="flex flex-col gap-6" style="padding: 4rem 1rem;">
      ${renderEmptyState({
        icon: icons.alertCircle(48),
        title: '404 - Page Not Found',
        description: 'The requested route does not exist or has been moved. Use the navigation links to return to safety.',
        actionText: 'Return to Dashboard',
        actionId: 'btn-404-dashboard'
      })}
    </div>
  `;

  container.querySelector('#btn-404-dashboard')?.addEventListener('click', () => {
    window.location.hash = '#dashboard';
  });
}

export function destroy() {}
