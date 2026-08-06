import { describe, it, expect, vi } from 'vitest';
import type { MorningBriefing } from '../../api/morning-briefing-api-types';
import {
  pickTopRecommendation,
  statusLabel,
} from '../morning-briefing-card-types';
import { createMorningBriefingCard } from '../morning-briefing-card-presentation';


// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeBriefing(overrides: Partial<MorningBriefing> = {}): MorningBriefing {
  return {
    generatedAt: '2026-08-06T12:00:00+00:00',
    status: 'ready',
    sections: [
      {
        title: 'Recovery',
        summary: 'Good recovery.',
        metrics: [{ title: 'Recovery score', value: 85, unit: '%', status: 'good' }],
        recommendations: [
          { title: 'Proceed as planned', description: 'Ok.', priority: 'low' },
        ],
      },
      {
        title: 'Training',
        summary: 'Easy run today.',
        metrics: [],
        recommendations: [],
      },
      {
        title: 'Biomarkers',
        summary: 'All within range.',
        metrics: [],
        recommendations: [],
      },
    ],
    ...overrides,
  };
}

const noop = () => {};

// ── pickTopRecommendation ─────────────────────────────────────────────────────

describe('pickTopRecommendation', () => {
  it('returns null when no recommendations exist', () => {
    const briefing = makeBriefing({
      sections: [{ title: 'A', summary: 'S', metrics: [], recommendations: [] }],
    });
    expect(pickTopRecommendation(briefing)).toBeNull();
  });

  it('picks highest priority: critical over high', () => {
    const briefing = makeBriefing({
      sections: [
        {
          title: 'A',
          summary: 'S',
          metrics: [],
          recommendations: [
            { title: 'High', description: 'D', priority: 'high' },
            { title: 'Critical', description: 'D', priority: 'critical' },
          ],
        },
      ],
    });
    const top = pickTopRecommendation(briefing);
    expect(top?.priority).toBe('critical');
    expect(top?.title).toBe('Critical');
  });

  it('picks highest priority across sections', () => {
    const briefing = makeBriefing({
      sections: [
        {
          title: 'A',
          summary: 'S',
          metrics: [],
          recommendations: [{ title: 'Low', description: 'D', priority: 'low' }],
        },
        {
          title: 'B',
          summary: 'S',
          metrics: [],
          recommendations: [{ title: 'High', description: 'D', priority: 'high' }],
        },
      ],
    });
    expect(pickTopRecommendation(briefing)?.priority).toBe('high');
  });

  it('returns null with empty briefing', () => {
    const briefing = makeBriefing({ sections: [] });
    expect(pickTopRecommendation(briefing)).toBeNull();
  });
});

// ── statusLabel ───────────────────────────────────────────────────────────────

describe('statusLabel', () => {
  it('ready → "Your briefing is ready."', () => {
    expect(statusLabel('ready')).toBe('Your briefing is ready.');
  });
  it('partial → "Some briefing data is unavailable."', () => {
    expect(statusLabel('partial')).toBe('Some briefing data is unavailable.');
  });
  it('unavailable → "Morning briefing is not available yet."', () => {
    expect(statusLabel('unavailable')).toBe('Morning briefing is not available yet.');
  });
  it('stale → "Some briefing data may be outdated."', () => {
    expect(statusLabel('stale')).toBe('Some briefing data may be outdated.');
  });
});

// ── createMorningBriefingCard ─────────────────────────────────────────────────

describe('createMorningBriefingCard', () => {
  it('renders loading skeleton with role="status"', () => {
    const card = createMorningBriefingCard({ kind: 'loading' }, noop, noop);
    expect(card.getAttribute('role')).toBe('status');
    expect(card.classList.contains('mb-card--loading')).toBe(true);
  });

  it('renders ready state with heading', () => {
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      noop,
    );
    expect(card.querySelector('h2')?.textContent).toBe('Morning Briefing');
    expect(card.classList.contains('mb-card--ready')).toBe(true);
  });

  it('renders partial state', () => {
    const briefing = makeBriefing({ status: 'partial' });
    const card = createMorningBriefingCard(
      { kind: 'partial', briefing, topRec: null },
      noop,
      noop,
    );
    expect(card.classList.contains('mb-card--partial')).toBe(true);
  });

  it('renders unavailable state', () => {
    const briefing = makeBriefing({ status: 'unavailable', sections: [] });
    const card = createMorningBriefingCard({ kind: 'unavailable', briefing }, noop, noop);
    expect(card.classList.contains('mb-card--unavailable')).toBe(true);
  });

  it('renders stale state', () => {
    const briefing = makeBriefing({ status: 'stale' });
    const card = createMorningBriefingCard(
      { kind: 'stale', briefing, topRec: { title: 'Refresh', priority: 'medium' } },
      noop,
      noop,
    );
    expect(card.classList.contains('mb-card--stale')).toBe(true);
  });

  it('renders failure state with role="alert"', () => {
    const card = createMorningBriefingCard(
      { kind: 'failure', errorMessage: 'err' },
      noop,
      noop,
    );
    expect(card.getAttribute('role')).toBe('alert');
    expect(card.classList.contains('mb-card--error')).toBe(true);
  });

  it('renders network_error state with role="alert"', () => {
    const card = createMorningBriefingCard(
      { kind: 'network_error', errorMessage: 'net err' },
      noop,
      noop,
    );
    expect(card.getAttribute('role')).toBe('alert');
  });

  it('renders invalid_data state without role="alert"', () => {
    const card = createMorningBriefingCard(
      { kind: 'invalid_data', errorMessage: 'bad data' },
      noop,
      noop,
    );
    expect(card.getAttribute('role')).not.toBe('alert');
  });

  it('shows max 3 section summaries', () => {
    const briefing = makeBriefing({
      status: 'ready',
      sections: [
        { title: 'S1', summary: 'Sum1', metrics: [], recommendations: [] },
        { title: 'S2', summary: 'Sum2', metrics: [], recommendations: [] },
        { title: 'S3', summary: 'Sum3', metrics: [], recommendations: [] },
        { title: 'S4', summary: 'Sum4', metrics: [], recommendations: [] },
      ],
    });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      noop,
    );
    const items = card.querySelectorAll('.mb-card__section-item');
    expect(items.length).toBe(3);
  });

  it('renders top recommendation when present', () => {
    const briefing = makeBriefing({ status: 'ready' });
    const topRec = { title: 'Prioritize recovery', priority: 'high' as const };
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec },
      noop,
      noop,
    );
    expect(card.querySelector('.mb-card__rec-row')).not.toBeNull();
    expect(card.querySelector('.mb-card__rec-title')?.textContent).toBe('Prioritize recovery');
    expect(card.querySelector('.mb-card__priority-badge')?.textContent).toBe('High');
  });

  it('does not render rec block when topRec is null', () => {
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      noop,
    );
    expect(card.querySelector('.mb-card__rec-section')).toBeNull();
  });

  it('Retry button calls onRetry', () => {
    const onRetry = vi.fn();
    const card = createMorningBriefingCard(
      { kind: 'failure', errorMessage: 'err' },
      onRetry,
      noop,
    );
    const btn = card.querySelector<HTMLButtonElement>('.mb-card__retry-btn');
    expect(btn).not.toBeNull();
    btn!.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('"View briefing" button calls onOpen on click', () => {
    const onOpen = vi.fn();
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      onOpen,
    );
    const btn = card.querySelector<HTMLButtonElement>('.mb-card__open-btn');
    expect(btn).not.toBeNull();
    btn!.click();
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('"View briefing" button calls onOpen on Enter', () => {
    const onOpen = vi.fn();
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      onOpen,
    );
    const btn = card.querySelector<HTMLButtonElement>('.mb-card__open-btn');
    btn!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('"View briefing" button calls onOpen on Space', () => {
    const onOpen = vi.fn();
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      onOpen,
    );
    const btn = card.querySelector<HTMLButtonElement>('.mb-card__open-btn');
    btn!.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('"View briefing" button has aria-label', () => {
    const briefing = makeBriefing({ status: 'ready' });
    const card = createMorningBriefingCard(
      { kind: 'ready', briefing, topRec: null },
      noop,
      noop,
    );
    const btn = card.querySelector<HTMLButtonElement>('.mb-card__open-btn');
    expect(btn?.getAttribute('aria-label')).toBeTruthy();
  });

  it('loading skeleton has aria-live="polite"', () => {
    const card = createMorningBriefingCard({ kind: 'loading' }, noop, noop);
    expect(card.getAttribute('aria-live')).toBe('polite');
  });

  it('loading skeleton has aria-busy="true"', () => {
    const card = createMorningBriefingCard({ kind: 'loading' }, noop, noop);
    expect(card.getAttribute('aria-busy')).toBe('true');
  });
});
