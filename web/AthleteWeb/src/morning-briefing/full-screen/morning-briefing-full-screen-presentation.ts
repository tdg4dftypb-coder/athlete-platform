import type { MorningBriefing } from '../api/morning-briefing-api-types';
import { statusLabel, formatGeneratedAt } from '../dashboard-card/morning-briefing-card-types';


const SECTION_LABELS: Record<string, string> = {
  Recovery: 'Regeneracja',
  Training: 'Trening',
  Biomarkers: 'Biomarkery',
};

const SECTION_TONES: Record<string, string> = {
  Recovery: 'recovery',
  Training: 'training',
  Biomarkers: 'biomarkers',
};

const METRIC_LABELS: Record<string, string> = {
  'Recovery score': 'Wynik regeneracji',
  'Recovery status': 'Status regeneracji',
  'Sleep quality': 'Jakość snu',
  'Session': 'Sesja',
  'Duration': 'Czas trwania',
  'Intensity': 'Intensywność',
  'Available results': 'Dostępne wyniki',
  'Results requiring attention': 'Wymagające uwagi',
};

const VALUE_LABELS: Record<string, string> = {
  Recovery: 'Regeneracja',
  Endurance: 'Wytrzymałość',
  Threshold: 'Próg',
  REST: 'Odpoczynek',
};

const RECOMMENDATION_LABELS: Record<string, string> = {
  'Refresh source data': 'Odśwież dane źródłowe',
  'Proceed as planned': 'Realizuj plan zgodnie z założeniami',
  'Train conservatively': 'Trenuj zachowawczo',
  'Prioritize recovery': 'Postaw na regenerację',
};

const RECOMMENDATION_DESCRIPTIONS: Record<string, string> = {
  'Some briefing information may be outdated.':
    'Część informacji w briefingu może być nieaktualna.',
  'Recovery indicators support today.':
    'Wskaźniki regeneracji wspierają realizację dzisiejszego planu.',
  'Recovery indicators support the planned training session.':
    'Wskaźniki regeneracji wspierają realizację zaplanowanej sesji.',
  "Keep today's training controlled and monitor how you feel.":
    'Utrzymaj dzisiejszy trening pod kontrolą i obserwuj samopoczucie.',
};

function localizeSummary(summary: string): string {
  return summary
    .replace(/Sport:\s*cycling/gi, 'Sport: kolarstwo')
    .replace(/Sport:\s*running/gi, 'Sport: bieganie')
    .replace(/Target TSS:/gi, 'Cel TSS:');
}

// ── Presentation state ────────────────────────────────────────────────────────

export type FullScreenState =
  | { kind: 'loading' }
  | { kind: 'ready' | 'partial' | 'stale'; briefing: MorningBriefing }
  | { kind: 'unavailable'; briefing: MorningBriefing }
  | { kind: 'failure'; errorMessage: string }
  | { kind: 'network_error'; errorMessage: string }
  | { kind: 'invalid_data'; errorMessage: string };

// ── Helpers ───────────────────────────────────────────────────────────────────

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  cls?: string,
  attrs?: Record<string, string>,
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  }
  return e;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function createLoadingSkeleton(): HTMLElement {
  const main = el('main', 'mb-full__main mb-full__main--loading');
  main.setAttribute('role', 'status');
  main.setAttribute('aria-label', 'Loading Morning Briefing…');
  main.setAttribute('aria-live', 'polite');
  main.setAttribute('aria-busy', 'true');

  for (const cls of [
    'mb-full__skeleton-header',
    'mb-full__skeleton-block mb-full__skeleton-block--tall',
    'mb-full__skeleton-block',
    'mb-full__skeleton-block mb-full__skeleton-block--short',
  ]) {
    main.appendChild(el('div', cls));
  }
  return main;
}

// ── Error / empty states ──────────────────────────────────────────────────────

function createErrorState(
  message: string,
  useAlertRole: boolean,
  onRetry: () => void,
  onBack: () => void,
): HTMLElement {
  const main = el('main', 'mb-full__main mb-full__main--error');
  if (useAlertRole) main.setAttribute('role', 'alert');

  const h1 = el('h1', 'mb-full__title');
  h1.setAttribute('tabindex', '-1');
  h1.textContent = 'Poranny briefing';

  const msg = el('p', 'mb-full__error-message');
  msg.textContent = message;

  const retryBtn = el('button', 'mb-full__btn mb-full__btn--primary');
  retryBtn.setAttribute('type', 'button');
  retryBtn.setAttribute('aria-label', 'Spróbuj ponownie wczytać poranny briefing');
  retryBtn.textContent = 'Spróbuj ponownie';
  retryBtn.addEventListener('click', onRetry);

  const backBtn = createBackButton(onBack);
  main.append(backBtn, h1, msg, retryBtn);
  return main;
}

// ── Back button ───────────────────────────────────────────────────────────────

function createBackButton(onBack: () => void): HTMLElement {
  const btn = el('button', 'mb-full__back-btn');
  btn.setAttribute('type', 'button');
  btn.setAttribute('aria-label', 'Powrót do pulpitu');
  btn.textContent = '← Powrót';
  btn.addEventListener('click', onBack);
  btn.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onBack(); }
  });
  return btn;
}

// ── Priority badge ────────────────────────────────────────────────────────────

type Priority = 'low' | 'medium' | 'high' | 'critical';

const PRIORITY_LABELS: Record<Priority, string> = {
  low: 'Niski',
  medium: 'Średni',
  high: 'Wysoki',
  critical: 'Krytyczny',
};

function createPriorityBadge(priority: Priority): HTMLElement {
  const badge = el('span', `mb-full__priority-badge mb-full__priority-badge--${priority}`);
  badge.textContent = PRIORITY_LABELS[priority];
  return badge;
}

// ── Metrics ───────────────────────────────────────────────────────────────────

function createMetricsList(metrics: MorningBriefing['sections'][number]['metrics']): HTMLElement {
  const list = el('ul', 'mb-full__metric-list');
  list.setAttribute('aria-label', 'Metrics');
  for (const metric of metrics) {
    const item = el('li', 'mb-full__metric-item');

    const title = el('span', 'mb-full__metric-title');
    title.textContent = METRIC_LABELS[metric.title] ?? metric.title;

    const valueWrap = el('span', 'mb-full__metric-value-wrap');
    const value = el('span', 'mb-full__metric-value');
    const rawValue = metric.value !== null && metric.value !== undefined
      ? String(metric.value)
      : '—';
    value.textContent = VALUE_LABELS[rawValue] ?? rawValue;

    if (metric.unit) {
      const unit = el('span', 'mb-full__metric-unit');
      unit.textContent = ` ${metric.unit}`;
      valueWrap.append(value, unit);
    } else {
      valueWrap.append(value);
    }

    item.append(title, valueWrap);
    list.appendChild(item);
  }
  return list;
}

// ── Recommendations ───────────────────────────────────────────────────────────

function createRecommendationsList(recs: MorningBriefing['sections'][number]['recommendations']): HTMLElement {
  const list = el('ul', 'mb-full__rec-list');
  list.setAttribute('aria-label', 'Recommendations');
  for (const rec of recs) {
    const item = el('li', 'mb-full__rec-item');

    const header = el('div', 'mb-full__rec-header');
    const title = el('span', 'mb-full__rec-title');
    title.textContent = RECOMMENDATION_LABELS[rec.title] ?? rec.title;
    header.append(title, createPriorityBadge(rec.priority as Priority));

    const desc = el('p', 'mb-full__rec-description');
    desc.textContent = RECOMMENDATION_DESCRIPTIONS[rec.description] ?? rec.description;

    item.append(header, desc);
    list.appendChild(item);
  }
  return list;
}

// ── Sections ──────────────────────────────────────────────────────────────────

function createSections(sections: MorningBriefing['sections']): HTMLElement {
  const container = el('div', 'mb-full__sections');

  for (const section of sections) {
    const tone = SECTION_TONES[section.title] ?? 'neutral';
    const label = SECTION_LABELS[section.title] ?? section.title;

    const article = el(
      'article',
      `mb-full__section mb-full__section--${tone}`,
    );
    article.setAttribute('aria-label', label);

    const heading = el('h2', 'mb-full__section-heading');
    heading.textContent = label;

    const summary = el('p', 'mb-full__section-summary');
    summary.textContent = localizeSummary(section.summary);

    article.append(heading, summary);

    if (section.metrics.length > 0) {
      article.appendChild(createMetricsList(section.metrics));
    }
    if (section.recommendations.length > 0) {
      const recHeading = el('h3', 'mb-full__rec-subheading');
      recHeading.textContent = 'Rekomendacje';
      article.append(recHeading, createRecommendationsList(section.recommendations));
    }

    container.appendChild(article);
  }
  return container;
}

// ── Content view ──────────────────────────────────────────────────────────────

function createContentView(
  briefing: MorningBriefing,
  onBack: () => void,
): HTMLElement {
  const main = el('main', `mb-full__main mb-full__main--${briefing.status}`);

  const backBtn = createBackButton(onBack);

  const h1 = el('h1', 'mb-full__title');
  h1.setAttribute('tabindex', '-1');
  h1.textContent = 'Poranny briefing';

  const meta = el('div', 'mb-full__meta');

  const statusEl = el('p', 'mb-full__status-label');
  statusEl.textContent = statusLabel(briefing.status);

  const genAt = el('p', 'mb-full__generated-at');
  genAt.textContent = `Briefing wygenerowany: ${formatGeneratedAt(briefing.generatedAt)}`;

  meta.append(statusEl, genAt);
  main.append(backBtn, h1, meta);

  if (briefing.sections.length > 0) {
    main.appendChild(createSections(briefing.sections));
  } else {
    const empty = el('p', 'mb-full__empty-message');
    empty.textContent = 'Brak dostępnych danych briefingu.';
    main.appendChild(empty);
  }

  return main;
}

// ── Public factory ────────────────────────────────────────────────────────────

export function createMorningBriefingFullScreen(
  state: FullScreenState,
  onRetry: () => void,
  onBack: () => void,
): HTMLElement {
  const shell = el('div', 'mb-full__shell');

  let content: HTMLElement;

  switch (state.kind) {
    case 'loading':
      content = createLoadingSkeleton();
      break;

    case 'ready':
    case 'partial':
    case 'stale':
    case 'unavailable':
      content = createContentView(state.briefing, onBack);
      break;

    case 'failure':
      content = createErrorState(
        'Nie udało się pobrać porannego briefingu. Spróbuj ponownie.',
        true,
        onRetry,
        onBack,
      );
      break;

    case 'network_error':
      content = createErrorState(
        'Nie udało się połączyć z serwerem danych. Sprawdź połączenie.',
        true,
        onRetry,
        onBack,
      );
      break;

    case 'invalid_data':
      content = createErrorState(
        'Dane porannego briefingu są chwilowo niedostępne.',
        false,
        onRetry,
        onBack,
      );
      break;
  }

  shell.appendChild(content);
  return shell;
}
