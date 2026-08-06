import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import type { PerformanceHistoryEntryWire } from '../../api/performance-lab-api-types';

import { createPerformanceLabHistoryPresentation } from '../performance-lab-history-presentation';
import { PerformanceLabHistoryContainer } from '../performance-lab-history-container';

const mockEntry: PerformanceHistoryEntryWire = {
  session: {
    test_id: 'lac-100',
    performed_at: '2026-08-01T10:00:00+00:00',
    test_type: 'lactate_step_test',
    status: 'completed',
    modality: 'cycling',
    protocol_name: '3-min step',
    body_mass_kg: 75.0,
    ambient_temperature_c: 21.0,
    notes: 'Good test',
    stages: [],
  },
  lactate_curve: null,
  threshold_analysis: {
    test_id: 'lac-100',
    lt1: {
      name: 'LT1',
      status: 'detected',
      stage_number: 2,
      power_watts: 200.0,
      speed_kph: null,
      heart_rate_bpm: 140,
      lactate_mmol_l: 2.1,
      target_lactate_mmol_l: 2.0,
      confidence: 0.6,
      method: 'fixed_2_mmol',
    },
    lt2: {
      name: 'LT2',
      status: 'not_reached',
      stage_number: null,
      power_watts: null,
      speed_kph: null,
      heart_rate_bpm: null,
      lactate_mmol_l: null,
      target_lactate_mmol_l: 4.0,
      confidence: null,
      method: 'fixed_4_mmol',
    },
  },
};

describe('createPerformanceLabHistoryPresentation', () => {
  it('renders loading state with role="status"', () => {
    const el = createPerformanceLabHistoryPresentation({ state: { kind: 'loading' } });
    const loading = el.querySelector('[role="status"]');
    expect(loading).not.toBeNull();
    expect(loading?.textContent).toContain('Wczytywanie');
  });

  it('renders empty state with exact text', () => {
    const el = createPerformanceLabHistoryPresentation({ state: { kind: 'empty' } });
    expect(el.textContent).toContain('No performance tests available.');
  });

  it('renders failure state with role="alert" and retry button', () => {
    const onRetry = vi.fn();
    const el = createPerformanceLabHistoryPresentation({
      state: { kind: 'failure', message: 'Custom error' },
      onRetry,
    });

    const alert = el.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain('Custom error');

    const btn = el.querySelector<HTMLButtonElement>('.pl-history__retry-btn');
    expect(btn).not.toBeNull();
    btn?.click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders ready state with session cards in reverse order (newest top)', () => {
    const entry2: PerformanceHistoryEntryWire = {
      ...mockEntry,
      session: {
        ...mockEntry.session,
        test_id: 'lac-200',
        performed_at: '2026-08-05T10:00:00+00:00',
      },
    };

    const onSelectSession = vi.fn();
    const el = createPerformanceLabHistoryPresentation({
      state: { kind: 'ready', entries: [mockEntry, entry2] },
      onSelectSession,
    });

    const cards = el.querySelectorAll('.pl-history-card');
    expect(cards.length).toBe(2);

    // Newest top: lac-200 performed at Aug 5, 2026 first
    expect(cards[0].getAttribute('aria-label')).toContain('5 sierpnia 2026');

    // Click card triggers onSelectSession
    (cards[0] as HTMLElement).click();
    expect(onSelectSession).toHaveBeenCalledWith('lac-200');

    // Original array order is unmutated
    expect(mockEntry.session.test_id).toBe('lac-100');
  });

  it('renders threshold pills with nieosiągnięty for NOT_REACHED', () => {
    const el = createPerformanceLabHistoryPresentation({
      state: { kind: 'ready', entries: [mockEntry] },
    });

    const pills = el.querySelectorAll('.pl-history-card__thresh-pill');
    expect(pills.length).toBe(2);
    expect(pills[0].textContent).toContain('LT1: 200 W');
    expect(pills[1].textContent).toContain('LT2: nieosiągnięty');
  });

  it('handles keyboard navigation (Enter key) on card', () => {
    const onSelectSession = vi.fn();
    const el = createPerformanceLabHistoryPresentation({
      state: { kind: 'ready', entries: [mockEntry] },
      onSelectSession,
    });

    const card = el.querySelector<HTMLElement>('.pl-history-card');
    expect(card).not.toBeNull();

    card?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(onSelectSession).toHaveBeenCalledWith('lac-100');
  });
});


describe('PerformanceLabHistoryContainer', () => {
  let rootEl: HTMLElement;

  beforeEach(() => {
    rootEl = document.createElement('div');
    document.body.appendChild(rootEl);
  });

  afterEach(() => {
    document.body.removeChild(rootEl);
  });

  it('fetches data and renders ready state', async () => {
    const stubClient = {
      getHistory: vi.fn().mockResolvedValue({
        success: true,
        data: { entries: [mockEntry] },
      }),
    };

    const container = new PerformanceLabHistoryContainer(rootEl, stubClient as any);
    await container.init();

    expect(stubClient.getHistory).toHaveBeenCalledTimes(1);
    expect(rootEl.querySelector('.pl-history-card')).not.toBeNull();
  });
});
