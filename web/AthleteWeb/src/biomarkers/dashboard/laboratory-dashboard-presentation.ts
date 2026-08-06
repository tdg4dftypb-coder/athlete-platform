import { createPageHeader } from '../../components/page-header';
import { createBottomNavigation } from '../../components/bottom-navigation';
import { searchForHistory } from '../../app/view-routing';
import { DashboardPresentationState } from './dashboard-types';

export function createLaboratoryDashboard(
  state: DashboardPresentationState,
  onBackToBriefing: () => void,
  onRetry?: () => void,
): HTMLElement {
  const shell = document.createElement('div');
  shell.className = 'app-shell biomarkers-shell';

  const main = document.createElement('main');
  main.className = 'briefing biomarkers-view';

  // Page Header
  const pageHeader = createPageHeader(
    {
      title: 'Wyniki badań',
      dateText: 'Laboratory Dashboard',
      lastUpdatedText: state.kind === 'ready' ? 'Zsynchronizowano' : 'Aktualizowanie...',
      freshnessLabel: null,
    },
    onBackToBriefing,
  );
  main.appendChild(pageHeader);

  // Content based on state kind
  switch (state.kind) {
    case 'loading': {
      const loadingSection = document.createElement('section');
      loadingSection.className = 'card card-loading biomarkers-skeleton';
      loadingSection.setAttribute('role', 'status');
      loadingSection.setAttribute('aria-live', 'polite');
      loadingSection.setAttribute('aria-busy', 'true');
      loadingSection.setAttribute('aria-label', 'Ładowanie wyników badań laboratoryjnych');

      loadingSection.innerHTML = `
        <div class="skeleton-pill" style="height: 1.5rem; width: 60%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 4px;"></div>
        <div class="skeleton-pill" style="height: 4rem; width: 100%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 8px;"></div>
        <div class="skeleton-pill" style="height: 8rem; width: 100%; background: var(--color-surface-muted); border-radius: 8px;"></div>
      `;
      main.appendChild(loadingSection);
      break;
    }

    case 'failure': {
      const failSection = document.createElement('section');
      failSection.className = 'card card-failure';
      failSection.setAttribute('role', 'alert');
      failSection.setAttribute('aria-live', 'assertive');

      const h2 = document.createElement('h2');
      h2.textContent = 'Błąd pobierania danych';
      h2.style.cssText = 'font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-primary);';
      failSection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.textContent = state.errorMessage || 'Wystąpił nieoczekiwany problem z połączeniem.';
      pMsg.style.cssText = 'color: var(--color-text-secondary); font-size: 0.9rem;';
      failSection.appendChild(pMsg);

      if (onRetry) {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn-retry';
        retryBtn.type = 'button';
        retryBtn.style.cssText = 'margin-top: 1rem; padding: 0.6rem 1.2rem; cursor: pointer; background: var(--color-surface-elevated); border: 1px solid var(--color-border); color: var(--color-text-primary); border-radius: 4px; font-weight: 600;';
        retryBtn.textContent = 'Spróbuj ponownie';
        retryBtn.addEventListener('click', onRetry);
        failSection.appendChild(retryBtn);
      }

      main.appendChild(failSection);
      break;
    }

    case 'empty': {
      const emptySection = document.createElement('section');
      emptySection.className = 'card card-empty';
      emptySection.setAttribute('role', 'status');
      emptySection.setAttribute('aria-live', 'polite');
      emptySection.style.cssText = 'text-align: center; padding: 2rem 1.2rem; background: var(--color-surface-muted); border-radius: 8px;';

      const h2 = document.createElement('h2');
      h2.style.cssText = 'font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-primary);';
      h2.textContent = 'Brak danych';
      emptySection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.style.cssText = 'color: var(--color-text-secondary); font-size: 0.9rem;';
      pMsg.textContent = 'Baza danych nie zawiera żadnych pomiarów laboratoryjnych.';
      emptySection.appendChild(pMsg);

      main.appendChild(emptySection);
      break;
    }

    case 'ready': {
      const listContainer = document.createElement('section');
      listContainer.className = 'card card-biomarkers-list';
      listContainer.style.cssText = 'padding: 1rem; background: var(--color-surface-muted); border-radius: 8px;';

      const bList = document.createElement('ul');
      bList.setAttribute('role', 'list');
      bList.setAttribute('aria-label', 'Lista biomarkerów laboratoryjnych');
      bList.style.cssText = 'list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.75rem;';

      for (const item of state.items) {
        const bLi = document.createElement('li');
        bLi.className = 'biomarker-item-row';
        bLi.style.cssText = 'padding: 0.75rem; border-radius: 6px; background: var(--color-surface-elevated); border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 0.35rem;';

        const mainRow = document.createElement('div');
        mainRow.style.cssText = 'display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;';

        const bName = document.createElement('span');
        bName.className = 'biomarker-name';
        bName.style.cssText = 'font-weight: 700; font-size: 0.9rem; flex: 1 1 auto; color: var(--color-text-primary); word-break: break-word;';
        bName.textContent = item.name;

        const bVal = document.createElement('span');
        bVal.className = 'biomarker-value';
        bVal.style.cssText = 'font-weight: 700; font-size: 0.95rem; text-align: right; margin-left: auto; flex: 0 0 auto; color: var(--color-text-primary);';
        
        if (item.latestValue !== null) {
          bVal.textContent = `${item.latestValue} ${item.unit}`.trim();
        } else {
          bVal.textContent = 'Brak danych';
        }

        mainRow.append(bName, bVal);

        const metaRow = document.createElement('div');
        metaRow.style.cssText = 'display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.78rem; color: var(--color-text-secondary); align-items: center;';

        if (item.collectedAt) {
          const dateSpan = document.createElement('span');
          dateSpan.className = 'biomarker-date';
          dateSpan.textContent = `Data: ${item.collectedAt}`;
          metaRow.appendChild(dateSpan);
        }

        const statusSpan = document.createElement('span');
        statusSpan.className = `biomarker-status status-${item.status}`;
        
        // WCAG AA Compliant High-Contrast Styles for badges
        let badgeBg = 'var(--color-surface-muted)';
        let badgeColor = 'var(--color-text-primary)';
        let statusLabel = 'Dane niepełne';

        if (item.status === 'normal') {
          statusLabel = 'W normie';
          badgeBg = 'var(--color-surface-muted)';
        } else if (item.status === 'attention') {
          statusLabel = 'Uwaga';
          badgeColor = 'var(--color-text-primary)';
          badgeBg = 'rgba(245, 158, 11, 0.15)'; // Soft amber background
        } else if (item.status === 'warning') {
          statusLabel = 'Ostrzeżenie';
          badgeColor = 'var(--color-text-primary)';
          badgeBg = 'rgba(239, 68, 68, 0.15)'; // Soft red background
        }
        
        statusSpan.style.cssText = `font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid var(--color-border); background: ${badgeBg}; color: ${badgeColor};`;
        statusSpan.textContent = statusLabel;
        metaRow.appendChild(statusSpan);

        bLi.append(mainRow, metaRow);

        // Click handler & accessibility to open history
        bLi.style.cursor = 'pointer';
        bLi.setAttribute('role', 'link');
        bLi.setAttribute('tabindex', '0');
        
        const latestValText = item.latestValue !== null ? `${item.latestValue} ${item.unit}` : 'Brak danych';
        const dateText = item.collectedAt ? `, pobrano: ${item.collectedAt}` : '';
        bLi.setAttribute('aria-label', `${item.name}, ostatni wynik: ${latestValText}${dateText}, status: ${statusLabel}. Kliknij, aby zobaczyć historię.`);

        const openHistory = () => {
          const url = new URL(window.location.href);
          url.search = searchForHistory(url.search, item.canonicalCode);
          window.history.pushState({ athleteView: 'history' }, '', url);
          window.dispatchEvent(new Event('popstate'));
        };

        bLi.addEventListener('click', openHistory);
        bLi.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openHistory();
          }
        });

        bList.appendChild(bLi);
      }

      listContainer.appendChild(bList);
      main.appendChild(listContainer);
      break;
    }
  }

  shell.appendChild(main);

  // Bottom Navigation
  const bottomNav = createBottomNavigation({ currentView: 'biomarkers' });
  shell.appendChild(bottomNav);

  return shell;
}
