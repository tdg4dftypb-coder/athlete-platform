import type { PerformanceHistoryEntryWire } from '../api/performance-lab-api-types';
import type { HistoryViewState } from './performance-lab-history-types';
import {
  formatDateLabel,
  formatModalityLabel,
  formatSessionStatusLabel,
  formatTestTypeLabel,
} from './performance-lab-history-types';

export interface PerformanceLabHistoryPresentationOptions {
  state: HistoryViewState;
  onRetry?: () => void;
  onSelectSession?: (testId: string) => void;
}

export function createPerformanceLabHistoryPresentation(
  options: PerformanceLabHistoryPresentationOptions
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'pl-history';

  const header = document.createElement('header');
  header.className = 'pl-history__header';

  const title = document.createElement('h1');
  title.className = 'pl-history__title';
  title.tabIndex = -1;
  title.textContent = 'Performance Lab — Historia testów';
  header.appendChild(title);

  container.appendChild(header);

  const content = document.createElement('div');
  content.className = 'pl-history__content';

  const { state, onRetry, onSelectSession } = options;

  switch (state.kind) {
    case 'loading': {
      content.appendChild(renderLoadingState());
      break;
    }
    case 'empty': {
      content.appendChild(renderEmptyState());
      break;
    }
    case 'ready': {
      content.appendChild(renderReadyState(state.entries, onSelectSession));
      break;
    }
    case 'failure': {
      content.appendChild(renderErrorState('Błąd serwera', state.message, onRetry));
      break;
    }
    case 'network_error': {
      content.appendChild(
        renderErrorState(
          'Błąd połączenia',
          'Nie można połączyć się z serwerem. Sprawdź połączenie z siecią.',
          onRetry
        )
      );
      break;
    }
    case 'invalid_data': {
      content.appendChild(
        renderErrorState(
          'Nieprawidłowe dane',
          'Otrzymano nieprawidłową strukturę danych z serwera.',
          onRetry
        )
      );
      break;
    }
  }

  container.appendChild(content);
  return container;
}

function renderLoadingState(): HTMLElement {
  const loadingEl = document.createElement('div');
  loadingEl.className = 'pl-history__state pl-history__state--loading';
  loadingEl.setAttribute('role', 'status');
  loadingEl.setAttribute('aria-live', 'polite');

  const spinner = document.createElement('div');
  spinner.className = 'pl-history__spinner';

  const label = document.createElement('span');
  label.textContent = 'Wczytywanie historii testów...';

  loadingEl.appendChild(spinner);
  loadingEl.appendChild(label);
  return loadingEl;
}

function renderEmptyState(): HTMLElement {
  const emptyEl = document.createElement('div');
  emptyEl.className = 'pl-history__state pl-history__state--empty';

  const p = document.createElement('p');
  p.className = 'pl-history__empty-text';
  p.textContent = 'No performance tests available.';

  emptyEl.appendChild(p);
  return emptyEl;
}

function renderErrorState(titleText: string, messageText: string, onRetry?: () => void): HTMLElement {
  const errorEl = document.createElement('div');
  errorEl.className = 'pl-history__state pl-history__state--error';
  errorEl.setAttribute('role', 'alert');

  const h3 = document.createElement('h3');
  h3.className = 'pl-history__error-title';
  h3.textContent = titleText;

  const p = document.createElement('p');
  p.className = 'pl-history__error-message';
  p.textContent = messageText;

  errorEl.appendChild(h3);
  errorEl.appendChild(p);

  if (onRetry) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pl-history__retry-btn';
    btn.setAttribute('aria-label', 'Spróbuj ponownie pobrać historię testów');
    btn.textContent = 'Spróbuj ponownie';
    btn.addEventListener('click', () => onRetry());
    errorEl.appendChild(btn);
  }

  return errorEl;
}

function renderReadyState(
  entries: PerformanceHistoryEntryWire[],
  onSelectSession?: (testId: string) => void
): HTMLElement {
  const readyEl = document.createElement('div');
  readyEl.className = 'pl-history__state pl-history__state--ready';

  const countBadge = document.createElement('div');
  countBadge.className = 'pl-history__count-badge';
  countBadge.textContent = `Liczba testów: ${entries.length}`;
  readyEl.appendChild(countBadge);

  // Present newest first (reverse of backend oldest->newest)
  const sortedEntries = [...entries].reverse();

  const list = document.createElement('div');
  list.className = 'pl-history__list';

  for (const entry of sortedEntries) {
    list.appendChild(renderSessionCard(entry, onSelectSession));
  }

  readyEl.appendChild(list);
  return readyEl;
}

function renderSessionCard(
  entry: PerformanceHistoryEntryWire,
  onSelectSession?: (testId: string) => void
): HTMLElement {
  const session = entry.session;
  const card = document.createElement('article');
  card.className = 'pl-history-card';
  card.tabIndex = 0;
  card.setAttribute('role', 'button');
  card.setAttribute(
    'aria-label',
    `Szczegóły testu ${formatTestTypeLabel(session.test_type)} z dnia ${formatDateLabel(session.performed_at)}`
  );

  const topRow = document.createElement('div');
  topRow.className = 'pl-history-card__top';

  const testType = document.createElement('h2');
  testType.className = 'pl-history-card__type';
  testType.textContent = formatTestTypeLabel(session.test_type);

  const statusBadge = document.createElement('span');
  statusBadge.className = `pl-history-card__status-badge pl-history-card__status-badge--${session.status}`;
  statusBadge.textContent = formatSessionStatusLabel(session.status);

  topRow.appendChild(testType);
  topRow.appendChild(statusBadge);
  card.appendChild(topRow);

  const metaRow = document.createElement('div');
  metaRow.className = 'pl-history-card__meta';

  const dateSpan = document.createElement('span');
  dateSpan.textContent = formatDateLabel(session.performed_at);

  const modalitySpan = document.createElement('span');
  modalitySpan.textContent = formatModalityLabel(session.modality);

  metaRow.appendChild(dateSpan);
  metaRow.appendChild(document.createTextNode(' • '));
  metaRow.appendChild(modalitySpan);

  if (session.protocol_name) {
    const protoSpan = document.createElement('span');
    protoSpan.className = 'pl-history-card__protocol';
    protoSpan.textContent = ` (${session.protocol_name})`;
    metaRow.appendChild(protoSpan);
  }

  card.appendChild(metaRow);

  // Summary thresholds if present
  if (entry.threshold_analysis) {
    const threshRow = document.createElement('div');
    threshRow.className = 'pl-history-card__thresholds';

    const lt1 = entry.threshold_analysis.lt1;
    const lt2 = entry.threshold_analysis.lt2;

    const lt1Pill = document.createElement('div');
    lt1Pill.className = 'pl-history-card__thresh-pill';
    lt1Pill.textContent = `LT1: ${formatThreshSummary(lt1)}`;

    const lt2Pill = document.createElement('div');
    lt2Pill.className = 'pl-history-card__thresh-pill';
    lt2Pill.textContent = `LT2: ${formatThreshSummary(lt2)}`;

    threshRow.appendChild(lt1Pill);
    threshRow.appendChild(lt2Pill);
    card.appendChild(threshRow);
  }

  const handleSelect = () => {
    if (onSelectSession) {
      onSelectSession(session.test_id);
    }
  };

  card.addEventListener('click', handleSelect);
  card.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSelect();
    }
  });

  return card;
}

function formatThreshSummary(thresh: { status: string; power_watts: number | null; speed_kph: number | null; lactate_mmol_l: number | null }): string {
  if (thresh.status !== 'detected') {
    return thresh.status === 'not_reached' ? 'nieosiągnięty' : 'brak danych';
  }
  if (thresh.power_watts !== null) {
    return `${thresh.power_watts} W`;
  }
  if (thresh.speed_kph !== null) {
    return `${thresh.speed_kph} km/h`;
  }
  if (thresh.lactate_mmol_l !== null) {
    return `${thresh.lactate_mmol_l} mmol/L`;
  }
  return 'wykryty';
}
