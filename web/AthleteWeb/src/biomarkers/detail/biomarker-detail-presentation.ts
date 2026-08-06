import { createPageHeader } from '../../components/page-header';
import { createBottomNavigation } from '../../components/bottom-navigation';
import { BiomarkerDetailState } from './detail-types';

export function createBiomarkerDetailView(
  state: BiomarkerDetailState,
  onBack: () => void,
  onRetry?: () => void,
): HTMLElement {
  const shell = document.createElement('div');
  shell.className = 'app-shell biomarkers-detail-shell';

  const main = document.createElement('main');
  main.className = 'briefing biomarker-detail-view';

  // Page Header
  const pageHeader = createPageHeader(
    {
      title: state.name || 'Szczegóły biomarkera',
      dateText: 'Laboratory Intelligence',
      lastUpdatedText: state.kind === 'ready' ? 'Zsynchronizowano' : 'Aktualizowanie...',
      freshnessLabel: null,
    },
    onBack,
  );
  main.appendChild(pageHeader);

  // Switch content based on state kind
  switch (state.kind) {
    case 'loading': {
      const loadingSection = document.createElement('section');
      loadingSection.className = 'card card-loading biomarkers-skeleton';
      loadingSection.setAttribute('role', 'status');
      loadingSection.setAttribute('aria-live', 'polite');
      loadingSection.setAttribute('aria-busy', 'true');
      loadingSection.setAttribute('aria-label', 'Ładowanie szczegółów biomarkera');

      loadingSection.innerHTML = `
        <div class="skeleton-pill" style="height: 1.5rem; width: 40%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 4px;"></div>
        <div class="skeleton-pill" style="height: 6rem; width: 100%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 8px;"></div>
        <div class="skeleton-pill" style="height: 10rem; width: 100%; background: var(--color-surface-muted); border-radius: 8px;"></div>
      `;
      main.appendChild(loadingSection);
      break;
    }

    case 'not_found': {
      const notFoundSection = document.createElement('section');
      notFoundSection.className = 'card card-not-found';
      notFoundSection.setAttribute('role', 'status');
      notFoundSection.setAttribute('aria-live', 'polite');
      notFoundSection.style.cssText = 'text-align: center; padding: 2rem 1.2rem; background: var(--color-surface-muted); border-radius: 8px;';

      const h2 = document.createElement('h2');
      h2.style.cssText = 'font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-primary);';
      h2.textContent = 'Biomarker nie istnieje';
      notFoundSection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.style.cssText = 'color: var(--color-text-secondary); font-size: 0.9rem;';
      pMsg.textContent = `Nie odnaleziono definicji ani pomiarów dla kodu: "${state.canonicalCode}".`;
      notFoundSection.appendChild(pMsg);

      main.appendChild(notFoundSection);
      break;
    }

    case 'network_error': {
      const netSection = document.createElement('section');
      netSection.className = 'card card-network-error';
      netSection.setAttribute('role', 'alert');
      netSection.setAttribute('aria-live', 'assertive');
      netSection.style.cssText = 'padding: 1.5rem; background: var(--color-surface-muted); border-radius: 8px; text-align: center;';

      const h2 = document.createElement('h2');
      h2.textContent = 'Brak połączenia z siecią';
      h2.style.cssText = 'font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-primary);';
      netSection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.textContent = state.errorMessage || 'Nie można nawiązać stabilnego połączenia z serwerem. Sprawdź swoje połączenie internetowe.';
      pMsg.style.cssText = 'color: var(--color-text-secondary); font-size: 0.9rem;';
      netSection.appendChild(pMsg);

      if (onRetry) {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn-retry';
        retryBtn.type = 'button';
        retryBtn.style.cssText = 'margin-top: 1rem; padding: 0.6rem 1.2rem; cursor: pointer; background: var(--color-surface-elevated); border: 1px solid var(--color-border); color: var(--color-text-primary); border-radius: 4px; font-weight: 600;';
        retryBtn.textContent = 'Spróbuj ponownie';
        retryBtn.addEventListener('click', onRetry);
        netSection.appendChild(retryBtn);
      }

      main.appendChild(netSection);
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
      h2.textContent = 'Brak historii pomiarów';
      emptySection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.style.cssText = 'color: var(--color-text-secondary); font-size: 0.9rem;';
      pMsg.textContent = 'Ten biomarker nie posiada jeszcze zarejestrowanych badań w historii.';
      emptySection.appendChild(pMsg);

      main.appendChild(emptySection);
      break;
    }

    case 'failure': {
      const failSection = document.createElement('section');
      failSection.className = 'card card-failure';
      failSection.setAttribute('role', 'alert');
      failSection.setAttribute('aria-live', 'assertive');

      const h2 = document.createElement('h2');
      h2.textContent = 'Błąd wczytywania szczegółów';
      h2.style.cssText = 'font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-primary);';
      failSection.appendChild(h2);

      const pMsg = document.createElement('p');
      pMsg.textContent = state.errorMessage || 'Wystąpił błąd synchronizacji z serwerem.';
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

    case 'partial':
    case 'ready': {
      // 1. Latest Measurement summary card
      const summaryCard = document.createElement('section');
      summaryCard.className = 'card card-summary';
      summaryCard.style.cssText = 'padding: 1.2rem; background: var(--color-surface-muted); border-radius: 8px; margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.5rem;';

      const labelSpan = document.createElement('small');
      labelSpan.style.cssText = 'color: var(--color-text-secondary); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;';
      labelSpan.textContent = 'Ostatni pomiar';

      const valDiv = document.createElement('div');
      valDiv.className = 'latest-value-display';
      valDiv.style.cssText = 'font-size: 2.2rem; font-weight: 800; color: var(--color-text-primary); line-height: 1;';
      
      if (state.latestValue !== undefined && state.latestValue !== null) {
        valDiv.textContent = `${state.latestValue} ${state.unit || ''}`.trim();
      } else {
        valDiv.textContent = 'Brak danych';
      }

      const dateSpan = document.createElement('span');
      dateSpan.style.cssText = 'color: var(--color-text-secondary); font-size: 0.8rem;';
      dateSpan.textContent = state.collectedAt ? `Pobrano: ${state.collectedAt}` : '';

      summaryCard.append(labelSpan, valDiv, dateSpan);
      main.appendChild(summaryCard);

      // 2. Trend summary card
      if (state.trend) {
        const trendCard = document.createElement('section');
        trendCard.className = 'card card-trend';
        trendCard.style.cssText = 'padding: 1.2rem; background: var(--color-surface-muted); border-radius: 8px; margin-bottom: 1rem;';

        const trendTitle = document.createElement('h3');
        trendTitle.style.cssText = 'font-size: 0.95rem; font-weight: 700; margin: 0 0 0.8rem 0; color: var(--color-text-primary);';
        trendTitle.textContent = 'Analiza trendu';
        trendCard.appendChild(trendTitle);

        const trendGrid = document.createElement('div');
        trendGrid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem;';

        const isInsufficient = state.trend.direction === 'insufficient_data';

        const directionIcon = {
          increasing: '↑',
          decreasing: '↓',
          stable: '→',
          insufficient_data: '?',
        }[state.trend.direction] || '?';

        const directionLabel = {
          increasing: 'Rosnący',
          decreasing: 'Malejący',
          stable: 'Stabilny',
          insufficient_data: 'Brak danych',
        }[state.trend.direction] || state.trend.direction;

        const strengthLabel = {
          none: 'Brak',
          weak: 'Słaby',
          moderate: 'Umiarkowany',
          strong: 'Silny',
        }[state.trend.strength] || state.trend.strength;

        const absChangeStr = !isInsufficient && state.trend.absoluteChange !== null
          ? (state.trend.absoluteChange >= 0 ? `+${state.trend.absoluteChange}` : `${state.trend.absoluteChange}`)
          : '—';

        const relChangeStr = !isInsufficient && state.trend.relativeChange !== null
          ? (state.trend.relativeChange >= 0 ? `+${state.trend.relativeChange}%` : `${state.trend.relativeChange}%`)
          : '—';

        // WCAG AA Compliant contrast color configuration for badges
        let badgeBg = 'var(--color-surface-muted)';
        let badgeColor = 'var(--color-text-primary)';
        if (state.trend.strength === 'strong') {
          badgeBg = 'rgba(239, 68, 68, 0.15)'; // high contrast soft red background
        } else if (state.trend.strength === 'moderate') {
          badgeBg = 'rgba(245, 158, 11, 0.15)'; // high contrast soft orange background
        } else if (state.trend.strength === 'weak') {
          badgeBg = 'rgba(59, 130, 246, 0.15)'; // high contrast soft blue background
        }

        trendGrid.innerHTML = `
          <div style="background: var(--color-surface-elevated); padding: 0.5rem; border-radius: 4px; border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 0.25rem;">
            <small style="color: var(--color-text-secondary); font-size: 0.72rem;">Kierunek</small>
            <div style="display: flex; align-items: center; gap: 0.35rem;">
              <span class="trend-direction-icon" style="font-size: 1.1rem; font-weight: 800; color: var(--color-text-primary);">${directionIcon}</span>
              <strong class="trend-direction" style="font-size: 0.88rem; color: var(--color-text-primary);">${directionLabel}</strong>
            </div>
          </div>
          <div style="background: var(--color-surface-elevated); padding: 0.5rem; border-radius: 4px; border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 0.25rem;">
            <small style="color: var(--color-text-secondary); font-size: 0.72rem;">Siła</small>
            <div>
              <span class="trend-strength-badge badge-strength-${state.trend.strength}" style="display: inline-block; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid var(--color-border); background: ${badgeBg}; color: ${badgeColor};">
                ${strengthLabel}
              </span>
            </div>
          </div>
          <div style="background: var(--color-surface-elevated); padding: 0.5rem; border-radius: 4px; border: 1px solid var(--color-border);">
            <small style="color: var(--color-text-secondary); display: block; font-size: 0.72rem;">Zmiana bezwzgl.</small>
            <strong class="trend-change-absolute" style="font-size: 0.88rem; color: var(--color-text-primary);">${absChangeStr} ${!isInsufficient && state.unit ? state.unit : ''}</strong>
          </div>
          <div style="background: var(--color-surface-elevated); padding: 0.5rem; border-radius: 4px; border: 1px solid var(--color-border);">
            <small style="color: var(--color-text-secondary); display: block; font-size: 0.72rem;">Zmiana względna</small>
            <strong class="trend-change-relative" style="font-size: 0.88rem; color: var(--color-text-primary);">${relChangeStr}</strong>
          </div>
        `;

        trendCard.appendChild(trendGrid);
        main.appendChild(trendCard);
      }

      // 2.5 Medical Insight Card
      if (state.insight) {
        const insightCard = document.createElement('section');
        insightCard.className = `card card-medical-insight interpretation-${state.insight.interpretation}`;
        
        let borderLeftColor = 'var(--color-border)';
        let insightBg = 'var(--color-surface-muted)';
        if (state.insight.interpretation === 'positive') {
          borderLeftColor = 'var(--color-success)';
          insightBg = 'rgba(34, 197, 94, 0.08)'; // WCAG AA soft success tint
        } else if (state.insight.interpretation === 'negative') {
          borderLeftColor = 'var(--color-danger, var(--color-warning))';
          insightBg = 'rgba(239, 68, 68, 0.08)'; // WCAG AA soft failure tint
        } else if (state.insight.interpretation === 'neutral') {
          borderLeftColor = 'var(--color-info)';
          insightBg = 'rgba(59, 130, 246, 0.08)'; // WCAG AA soft info tint
        }

        insightCard.style.cssText = `padding: 1.2rem; background: ${insightBg}; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid ${borderLeftColor}; display: flex; flex-direction: column; gap: 0.5rem;`;

        const headerDiv = document.createElement('div');
        headerDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: baseline;';

        const insightTitle = document.createElement('h3');
        insightTitle.style.cssText = 'font-size: 0.95rem; font-weight: 700; margin: 0; color: var(--color-text-primary);';
        insightTitle.textContent = 'Interpretacja medyczna';

        const confidenceBadge = document.createElement('span');
        confidenceBadge.className = `insight-confidence-badge confidence-${state.insight.confidence}`;
        confidenceBadge.style.cssText = 'font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid var(--color-border); background: var(--color-surface-elevated); color: var(--color-text-primary);';
        
        const confidenceLabel = {
          none: 'Pewność: brak',
          low: 'Pewność: niska',
          medium: 'Pewność: średnia',
          high: 'Pewność: wysoka',
        }[state.insight.confidence] || `Pewność: ${state.insight.confidence}`;
        
        confidenceBadge.textContent = confidenceLabel;
        headerDiv.append(insightTitle, confidenceBadge);
        insightCard.appendChild(headerDiv);

        if (state.insight.summary) {
          const summaryP = document.createElement('p');
          summaryP.className = 'insight-summary';
          summaryP.style.cssText = 'font-weight: 700; font-size: 0.9rem; color: var(--color-text-primary); margin: 0.2rem 0 0 0;';
          summaryP.textContent = state.insight.summary;
          insightCard.appendChild(summaryP);
        }

        if (state.insight.reasoning) {
          const reasoningP = document.createElement('p');
          reasoningP.className = 'insight-reasoning';
          reasoningP.style.cssText = 'font-size: 0.85rem; color: var(--color-text-secondary); margin: 0;';
          reasoningP.textContent = state.insight.reasoning;
          insightCard.appendChild(reasoningP);
        }

        main.appendChild(insightCard);
      }

      if (state.kind === 'partial') {
        const partialNotice = document.createElement('section');
        partialNotice.className = 'card card-notice warning-notice';
        partialNotice.setAttribute('role', 'alert');
        partialNotice.setAttribute('aria-live', 'assertive');
        partialNotice.style.cssText = 'border-left: 4px solid var(--color-warning); padding: 0.8rem 1rem; margin-bottom: 1rem; background: rgba(245, 158, 11, 0.1); border-radius: 8px; color: var(--color-text-primary); font-size: 0.88rem; font-weight: 500;';
        partialNotice.textContent = 'Interpretacja kliniczna oraz trendy są chwilowo niedostępne.';
        main.appendChild(partialNotice);
      }

      // 3. History list card
      if (state.history && state.history.length > 0) {
        const historyCard = document.createElement('section');
        historyCard.className = 'card card-history';
        historyCard.style.cssText = 'padding: 1.2rem; background: var(--color-surface-muted); border-radius: 8px;';

        const historyTitle = document.createElement('h3');
        historyTitle.style.cssText = 'font-size: 0.95rem; font-weight: 700; margin: 0 0 0.8rem 0; color: var(--color-text-primary);';
        historyTitle.textContent = 'Historia pomiarów';
        historyCard.appendChild(historyTitle);

        const table = document.createElement('table');
        table.setAttribute('aria-label', `Historia pomiarów: ${state.name || 'biomarker'}`);
        table.style.cssText = 'width: 100%; border-collapse: collapse; font-size: 0.88rem;';

        const tbody = document.createElement('tbody');

        for (const item of state.history) {
          const tr = document.createElement('tr');
          tr.className = 'history-row';
          tr.style.cssText = 'border-bottom: 1px solid var(--color-border);';

          const tdDate = document.createElement('td');
          tdDate.style.cssText = 'padding: 0.6rem 0; color: var(--color-text-secondary);';
          tdDate.textContent = item.date;

          const tdVal = document.createElement('td');
          tdVal.style.cssText = 'padding: 0.6rem 0; text-align: right; font-weight: 700; color: var(--color-text-primary);';
          tdVal.textContent = `${item.value} ${state.unit || ''}`.trim();

          tr.append(tdDate, tdVal);
          tbody.appendChild(tr);
        }

        table.appendChild(tbody);
        historyCard.appendChild(table);
        main.appendChild(historyCard);
      }
      break;
    }
  }

  shell.appendChild(main);

  // Bottom Navigation
  const bottomNav = createBottomNavigation({ currentView: 'biomarkers' });
  shell.appendChild(bottomNav);

  return shell;
}
