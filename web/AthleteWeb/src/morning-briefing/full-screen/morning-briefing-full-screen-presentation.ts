import type { MorningBriefing } from '../api/morning-briefing-api-types';
import { statusLabel, formatGeneratedAt } from '../dashboard-card/morning-briefing-card-types';


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
  h1.textContent = 'Morning Briefing';

  const msg = el('p', 'mb-full__error-message');
  msg.textContent = message;

  const retryBtn = el('button', 'mb-full__btn mb-full__btn--primary');
  retryBtn.setAttribute('type', 'button');
  retryBtn.setAttribute('aria-label', 'Retry loading Morning Briefing');
  retryBtn.textContent = 'Retry';
  retryBtn.addEventListener('click', onRetry);

  const backBtn = createBackButton(onBack);
  main.append(backBtn, h1, msg, retryBtn);
  return main;
}

// ── Back button ───────────────────────────────────────────────────────────────

function createBackButton(onBack: () => void): HTMLElement {
  const btn = el('button', 'mb-full__back-btn');
  btn.setAttribute('type', 'button');
  btn.setAttribute('aria-label', 'Back to dashboard');
  btn.textContent = '← Back';
  btn.addEventListener('click', onBack);
  btn.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onBack(); }
  });
  return btn;
}

// ── Priority badge ────────────────────────────────────────────────────────────

type Priority = 'low' | 'medium' | 'high' | 'critical';

function createPriorityBadge(priority: Priority): HTMLElement {
  const badge = el('span', `mb-full__priority-badge mb-full__priority-badge--${priority}`);
  badge.textContent = priority.charAt(0).toUpperCase() + priority.slice(1);
  return badge;
}

// ── Metrics ───────────────────────────────────────────────────────────────────

function createMetricsList(metrics: MorningBriefing['sections'][number]['metrics']): HTMLElement {
  const list = el('ul', 'mb-full__metric-list');
  list.setAttribute('aria-label', 'Metrics');
  for (const metric of metrics) {
    const item = el('li', 'mb-full__metric-item');

    const title = el('span', 'mb-full__metric-title');
    title.textContent = metric.title;

    const valueWrap = el('span', 'mb-full__metric-value-wrap');
    const value = el('span', 'mb-full__metric-value');
    value.textContent = metric.value !== null && metric.value !== undefined
      ? String(metric.value)
      : '—';

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
    title.textContent = rec.title;
    header.append(title, createPriorityBadge(rec.priority as Priority));

    const desc = el('p', 'mb-full__rec-description');
    desc.textContent = rec.description;

    item.append(header, desc);
    list.appendChild(item);
  }
  return list;
}

// ── Sections ──────────────────────────────────────────────────────────────────

function createSections(sections: MorningBriefing['sections']): HTMLElement {
  const container = el('div', 'mb-full__sections');

  for (const section of sections) {
    const article = el('article', 'mb-full__section');
    article.setAttribute('aria-label', section.title);

    const heading = el('h2', 'mb-full__section-heading');
    heading.textContent = section.title;

    const summary = el('p', 'mb-full__section-summary');
    summary.textContent = section.summary;

    article.append(heading, summary);

    if (section.metrics.length > 0) {
      article.appendChild(createMetricsList(section.metrics));
    }
    if (section.recommendations.length > 0) {
      const recHeading = el('h3', 'mb-full__rec-subheading');
      recHeading.textContent = 'Recommendations';
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
  h1.textContent = 'Morning Briefing';

  const meta = el('div', 'mb-full__meta');

  const statusEl = el('p', 'mb-full__status-label');
  statusEl.textContent = statusLabel(briefing.status);

  const genAt = el('p', 'mb-full__generated-at');
  genAt.textContent = `Updated: ${formatGeneratedAt(briefing.generatedAt)}`;

  meta.append(statusEl, genAt);
  main.append(backBtn, h1, meta);

  if (briefing.sections.length > 0) {
    main.appendChild(createSections(briefing.sections));
  } else {
    const empty = el('p', 'mb-full__empty-message');
    empty.textContent = 'No briefing data available.';
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
        'Failed to load Morning Briefing. Please try again.',
        true,
        onRetry,
        onBack,
      );
      break;

    case 'network_error':
      content = createErrorState(
        'Morning Briefing could not be loaded. Check your connection.',
        true,
        onRetry,
        onBack,
      );
      break;

    case 'invalid_data':
      content = createErrorState(
        'Morning Briefing data is temporarily unavailable.',
        false,
        onRetry,
        onBack,
      );
      break;
  }

  shell.appendChild(content);
  return shell;
}
