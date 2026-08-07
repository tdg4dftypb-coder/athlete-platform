import type { MorningBriefing, MorningBriefingPriority } from '../api/morning-briefing-api-types';
import type { CardState, TopRecommendation } from './morning-briefing-card-types';
import { statusLabel, formatGeneratedAt } from './morning-briefing-card-types';

const MAX_SECTION_SUMMARIES = 3;

const SECTION_LABELS: Record<string, string> = {
  Recovery: 'Regeneracja',
  Training: 'Trening',
  Biomarkers: 'Biomarkery',
};

const RECOMMENDATION_LABELS: Record<string, string> = {
  'Refresh source data': 'Odśwież dane źródłowe',
  'Proceed as planned': 'Realizuj plan zgodnie z założeniami',
};

const PRIORITY_LABELS: Record<MorningBriefingPriority, string> = {
  low: 'Niski',
  medium: 'Średni',
  high: 'Wysoki',
  critical: 'Krytyczny',
};

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, attrs?: Record<string, string>): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      e.setAttribute(k, v);
    }
  }
  return e;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function createSkeletonCard(): HTMLElement {
  const card = el('div', 'mb-card mb-card--loading');
  card.setAttribute('role', 'status');
  card.setAttribute('aria-label', 'Loading Morning Briefing…');
  card.setAttribute('aria-live', 'polite');
  card.setAttribute('aria-busy', 'true');

  const header = el('div', 'mb-card__skeleton-header');
  const line1 = el('div', 'mb-card__skeleton-line mb-card__skeleton-line--title');
  const line2 = el('div', 'mb-card__skeleton-line mb-card__skeleton-line--subtitle');
  const body = el('div', 'mb-card__skeleton-body');
  const line3 = el('div', 'mb-card__skeleton-line');
  const line4 = el('div', 'mb-card__skeleton-line mb-card__skeleton-line--short');

  header.append(line1, line2);
  body.append(line3, line4);
  card.append(header, body);
  return card;
}

// ── Priority badge ────────────────────────────────────────────────────────────

function createPriorityBadge(priority: MorningBriefingPriority): HTMLElement {
  const badge = el('span', `mb-card__priority-badge mb-card__priority-badge--${priority}`);
  badge.textContent = PRIORITY_LABELS[priority];
  return badge;
}

// ── Recommendation row ────────────────────────────────────────────────────────

function createTopRecRow(topRec: TopRecommendation): HTMLElement {
  const row = el('div', 'mb-card__rec-row');
  const title = el('span', 'mb-card__rec-title');
  title.textContent = RECOMMENDATION_LABELS[topRec.title] ?? topRec.title;
  row.append(title, createPriorityBadge(topRec.priority));
  return row;
}

// ── Error state ───────────────────────────────────────────────────────────────

function createErrorCard(
  message: string,
  isAlert: boolean,
  onRetry: () => void,
): HTMLElement {
  const card = el('div', 'mb-card mb-card--error');
  if (isAlert) card.setAttribute('role', 'alert');

  const heading = el('h2', 'mb-card__heading');
  heading.textContent = 'Poranny briefing';

  const msg = el('p', 'mb-card__error-message');
  msg.textContent = message;

  const retryBtn = el('button', 'mb-card__retry-btn');
  retryBtn.textContent = 'Spróbuj ponownie';
  retryBtn.setAttribute('type', 'button');
  retryBtn.addEventListener('click', onRetry);

  card.append(heading, msg, retryBtn);
  return card;
}

// ── Content card ──────────────────────────────────────────────────────────────

function createContentCard(
  state: Extract<CardState, { kind: 'ready' | 'partial' | 'unavailable' | 'stale' }>,
  onOpen: () => void,
): HTMLElement {
  const briefing: MorningBriefing = state.briefing;
  const card = el('div', `mb-card mb-card--${briefing.status}`);
  card.setAttribute('role', 'region');
  card.setAttribute('aria-label', 'Morning Briefing card');

  // Heading
  const heading = el('h2', 'mb-card__heading');
  heading.textContent = 'Poranny briefing';

  // Status label
  const statusEl = el('p', 'mb-card__status-label');
  statusEl.textContent = statusLabel(briefing.status);

  // Generated at
  const genAt = el('p', 'mb-card__generated-at');
  genAt.textContent = `Briefing wygenerowany: ${formatGeneratedAt(briefing.generatedAt)}`;

  card.append(heading, statusEl, genAt);

  // Section summaries (max 3)
  const visibleSections = briefing.sections.slice(0, MAX_SECTION_SUMMARIES);
  if (visibleSections.length > 0) {
    const sectList = el('ul', 'mb-card__section-list');
    sectList.setAttribute('aria-label', 'Briefing sections');
    for (const section of visibleSections) {
      const item = el('li', 'mb-card__section-item');
      const sectionTitle = el('span', 'mb-card__section-title');
      sectionTitle.textContent = SECTION_LABELS[section.title] ?? section.title;
      const sectionSummary = el('span', 'mb-card__section-summary');
      sectionSummary.textContent = section.summary;
      item.append(sectionTitle, sectionSummary);
      sectList.appendChild(item);
    }
    card.appendChild(sectList);
  }

  // Top recommendation
  const topRec = 'topRec' in state ? state.topRec : null;
  if (topRec) {
    const recSection = el('div', 'mb-card__rec-section');
    recSection.setAttribute('aria-label', 'Top recommendation');
    recSection.appendChild(createTopRecRow(topRec));
    card.appendChild(recSection);
  }

  // "View briefing" button
  const openBtn = el('button', 'mb-card__open-btn');
  openBtn.textContent = 'Zobacz briefing';
  openBtn.setAttribute('type', 'button');
  openBtn.setAttribute('aria-label', 'Otwórz pełny poranny briefing');
  openBtn.addEventListener('click', onOpen);
  openBtn.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpen();
    }
  });

  card.appendChild(openBtn);
  return card;
}

// ── Public factory ────────────────────────────────────────────────────────────

export function createMorningBriefingCard(
  state: CardState,
  onRetry: () => void,
  onOpen: () => void,
): HTMLElement {
  switch (state.kind) {
    case 'loading':
      return createSkeletonCard();

    case 'ready':
    case 'partial':
    case 'unavailable':
    case 'stale':
      return createContentCard(state, onOpen);

    case 'failure':
      return createErrorCard(
        'Nie udało się pobrać porannego briefingu. Spróbuj ponownie.',
        true,
        onRetry,
      );

    case 'network_error':
      return createErrorCard(
        'Nie udało się połączyć z serwerem danych. Sprawdź połączenie.',
        true,
        onRetry,
      );

    case 'invalid_data':
      return createErrorCard(
        'Dane porannego briefingu są chwilowo niedostępne.',
        false,
        onRetry,
      );
  }
}
