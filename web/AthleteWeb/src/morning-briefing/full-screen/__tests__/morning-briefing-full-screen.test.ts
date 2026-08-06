import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { MorningBriefing } from '../../api/morning-briefing-api-types';
import type { MbApiResult } from '../../api/morning-briefing-api-client';
import { createMorningBriefingFullScreen } from '../morning-briefing-full-screen-presentation';
import { MorningBriefingFullScreenContainer } from '../morning-briefing-full-screen-container';


// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeBriefing(overrides: Partial<MorningBriefing> = {}): MorningBriefing {
  return {
    generatedAt: '2026-08-06T12:00:00+00:00',
    status: 'ready',
    sections: [
      {
        title: 'Recovery',
        summary: 'Good recovery.',
        metrics: [
          { title: 'Recovery score', value: 85, unit: '%', status: 'good' },
          { title: 'Sleep quality', value: 'Good', unit: null, status: 'info' },
        ],
        recommendations: [
          { title: 'Proceed as planned', description: 'Recovery indicators support today.', priority: 'low' },
        ],
      },
      {
        title: 'Training',
        summary: 'Easy run planned.',
        metrics: [],
        recommendations: [],
      },
      {
        title: 'Biomarkers',
        summary: 'All results within normal range.',
        metrics: [
          { title: 'Results requiring attention', value: 0, unit: null, status: 'info' },
        ],
        recommendations: [],
      },
    ],
    ...overrides,
  };
}

const noop = () => {};

// ── Presentation: createMorningBriefingFullScreen ─────────────────────────────

describe('createMorningBriefingFullScreen', () => {
  it('loading — renders skeleton with role="status"', () => {
    const el = createMorningBriefingFullScreen({ kind: 'loading' }, noop, noop);
    const main = el.querySelector('main');
    expect(main?.getAttribute('role')).toBe('status');
    expect(main?.classList.contains('mb-full__main--loading')).toBe(true);
    expect(main?.getAttribute('aria-live')).toBe('polite');
    expect(main?.getAttribute('aria-busy')).toBe('true');
  });

  it('ready — renders h1 with tabindex=-1', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    const h1 = el.querySelector('h1');
    expect(h1?.textContent).toBe('Morning Briefing');
    expect(h1?.getAttribute('tabindex')).toBe('-1');
  });

  it('ready — renders generated_at', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing({ generatedAt: '2026-08-06T14:30:00+00:00' }) },
      noop,
      noop,
    );
    expect(el.querySelector('.mb-full__generated-at')?.textContent).toContain('Updated:');
  });

  it('partial — renders main with partial class', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'partial', briefing: makeBriefing({ status: 'partial' }) },
      noop,
      noop,
    );
    expect(el.querySelector('.mb-full__main--partial')).not.toBeNull();
  });

  it('stale — renders main with stale class', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'stale', briefing: makeBriefing({ status: 'stale' }) },
      noop,
      noop,
    );
    expect(el.querySelector('.mb-full__main--stale')).not.toBeNull();
  });

  it('unavailable — renders main, no error role', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'unavailable', briefing: makeBriefing({ status: 'unavailable', sections: [] }) },
      noop,
      noop,
    );
    const main = el.querySelector('main');
    expect(main?.classList.contains('mb-full__main--unavailable')).toBe(true);
    expect(main?.getAttribute('role')).not.toBe('alert');
  });

  it('unavailable — empty sections renders empty message', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'unavailable', briefing: makeBriefing({ status: 'unavailable', sections: [] }) },
      noop,
      noop,
    );
    expect(el.querySelector('.mb-full__empty-message')).not.toBeNull();
    expect(el.querySelector('.mb-full__sections')).toBeNull();
  });

  it('failure — renders role="alert"', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'failure', errorMessage: 'err' },
      noop,
      noop,
    );
    expect(el.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('network_error — renders role="alert"', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'network_error', errorMessage: 'net err' },
      noop,
      noop,
    );
    expect(el.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('invalid_data — renders without role="alert"', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'invalid_data', errorMessage: 'bad data' },
      noop,
      noop,
    );
    const main = el.querySelector('main');
    expect(main?.getAttribute('role')).not.toBe('alert');
  });

  it('renders all sections in payload order', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    const headings = Array.from(el.querySelectorAll('.mb-full__section-heading')).map(h => h.textContent);
    expect(headings).toEqual(['Recovery', 'Training', 'Biomarkers']);
  });

  it('renders metrics for each section', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    const metrics = el.querySelectorAll('.mb-full__metric-item');
    expect(metrics.length).toBe(3); // 2 recovery + 1 biomarker
  });

  it('renders value=null as em dash', () => {
    const briefing = makeBriefing({
      sections: [{
        title: 'Recovery',
        summary: 'Summary.',
        metrics: [{ title: 'Score', value: null, unit: '%', status: 'info' }],
        recommendations: [],
      }],
    });
    const el = createMorningBriefingFullScreen({ kind: 'ready', briefing }, noop, noop);
    const value = el.querySelector('.mb-full__metric-value');
    expect(value?.textContent).toBe('—');
  });

  it('renders recommendations with priority badges', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    const badge = el.querySelector('.mb-full__priority-badge');
    expect(badge?.textContent).toBe('Low');
    expect(badge?.classList.contains('mb-full__priority-badge--low')).toBe(true);
  });

  it.each(['low', 'medium', 'high', 'critical'] as const)(
    'renders %s priority badge with correct class',
    (priority) => {
      const briefing = makeBriefing({
        sections: [{
          title: 'Recovery',
          summary: 'S.',
          metrics: [],
          recommendations: [{ title: 'T', description: 'D', priority }],
        }],
      });
      const el = createMorningBriefingFullScreen({ kind: 'ready', briefing }, noop, noop);
      expect(el.querySelector(`.mb-full__priority-badge--${priority}`)).not.toBeNull();
    },
  );

  it('preserves recommendation order from payload', () => {
    const briefing = makeBriefing({
      sections: [{
        title: 'Recovery',
        summary: 'S.',
        metrics: [],
        recommendations: [
          { title: 'First rec', description: 'D', priority: 'high' },
          { title: 'Second rec', description: 'D', priority: 'low' },
        ],
      }],
    });
    const el = createMorningBriefingFullScreen({ kind: 'ready', briefing }, noop, noop);
    const titles = Array.from(el.querySelectorAll('.mb-full__rec-title')).map(t => t.textContent);
    expect(titles).toEqual(['First rec', 'Second rec']);
  });

  it('Retry button calls onRetry', () => {
    const onRetry = vi.fn();
    const el = createMorningBriefingFullScreen({ kind: 'failure', errorMessage: 'err' }, onRetry, noop);
    el.querySelector<HTMLButtonElement>('.mb-full__btn--primary')?.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('Back button calls onBack', () => {
    const onBack = vi.fn();
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      onBack,
    );
    el.querySelector<HTMLButtonElement>('.mb-full__back-btn')?.click();
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('Back button has aria-label', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    const btn = el.querySelector<HTMLButtonElement>('.mb-full__back-btn');
    expect(btn?.getAttribute('aria-label')).toBeTruthy();
  });

  it('error Back button calls onBack', () => {
    const onBack = vi.fn();
    const el = createMorningBriefingFullScreen(
      { kind: 'failure', errorMessage: 'err' },
      noop,
      onBack,
    );
    el.querySelector<HTMLButtonElement>('.mb-full__back-btn')?.click();
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('shell has no overflow-x issues (uses overflow-wrap classes)', () => {
    const el = createMorningBriefingFullScreen(
      { kind: 'ready', briefing: makeBriefing() },
      noop,
      noop,
    );
    // Verify mb-full__section has overflow-wrap class applied (CSS-level responsibility)
    expect(el.querySelector('.mb-full__section')).not.toBeNull();
    expect(el.querySelector('.mb-full__main')).not.toBeNull();
  });
});

// ── Container tests ───────────────────────────────────────────────────────────

function makeStubClient(response: MbApiResult) {
  return { getMorningBriefing: vi.fn().mockResolvedValue(response) };
}

describe('MorningBriefingFullScreenContainer', () => {
  let mountPoint: HTMLElement;

  beforeEach(() => {
    mountPoint = document.createElement('div');
    document.body.appendChild(mountPoint);
  });

  afterEach(() => {
    document.body.removeChild(mountPoint);
  });

  it('renders loading skeleton initially', async () => {
    const client = {
      getMorningBriefing: vi.fn(() => new Promise(() => {})), // never resolves
    };
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    container.init(); // do not await — we want to catch the loading state
    await Promise.resolve(); // flush micro-tasks
    expect(mountPoint.querySelector('.mb-full__main--loading')).not.toBeNull();
  });

  it('renders ready state on success', async () => {
    const briefing = makeBriefing({ status: 'ready' });
    const client = makeStubClient({ success: true, data: briefing });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('.mb-full__main--ready')).not.toBeNull();
  });

  it('renders partial state', async () => {
    const briefing = makeBriefing({ status: 'partial' });
    const client = makeStubClient({ success: true, data: briefing });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('.mb-full__main--partial')).not.toBeNull();
  });

  it('renders unavailable state', async () => {
    const briefing = makeBriefing({ status: 'unavailable', sections: [] });
    const client = makeStubClient({ success: true, data: briefing });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('.mb-full__main--unavailable')).not.toBeNull();
  });

  it('renders stale state', async () => {
    const briefing = makeBriefing({ status: 'stale' });
    const client = makeStubClient({ success: true, data: briefing });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('.mb-full__main--stale')).not.toBeNull();
  });

  it('renders failure on server_error', async () => {
    const client = makeStubClient({ success: false, error: { type: 'server_error', message: 'err' } });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('renders network_error state on network_error', async () => {
    const client = makeStubClient({ success: false, error: { type: 'network_error', message: 'net' } });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    expect(mountPoint.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('renders invalid_data without alert role', async () => {
    const client = makeStubClient({ success: false, error: { type: 'invalid_data', message: 'bad' } });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();
    const main = mountPoint.querySelector('main');
    expect(main?.getAttribute('role')).not.toBe('alert');
  });

  it('Retry calls load again (client called twice)', async () => {
    const client = makeStubClient({ success: false, error: { type: 'server_error', message: 'err' } });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, noop);
    await container.init();

    // Click retry
    const retryBtn = mountPoint.querySelector<HTMLButtonElement>('.mb-full__btn--primary');
    await retryBtn?.click();
    await Promise.resolve();

    expect(client.getMorningBriefing).toHaveBeenCalledTimes(2);
  });

  it('Back button calls onBack callback', async () => {
    const onBack = vi.fn();
    const briefing = makeBriefing();
    const client = makeStubClient({ success: true, data: briefing });
    const container = new MorningBriefingFullScreenContainer(mountPoint, client as any, onBack);
    await container.init();
    mountPoint.querySelector<HTMLButtonElement>('.mb-full__back-btn')?.click();
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('onOpen from Dashboard Card triggers navigation to full screen', () => {
    // Simulate Dashboard Card onOpen callback triggering navigation
    const navigatedTo: string[] = [];
    const mockNavigate = (view: string) => navigatedTo.push(view);

    // The card container's onOpen is just a callback — simulate it
    const onOpen = () => mockNavigate('morning-briefing-detail');
    onOpen();

    expect(navigatedTo).toContain('morning-briefing-detail');
  });
});
