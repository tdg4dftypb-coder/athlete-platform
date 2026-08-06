import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import type { PerformanceHistoryEntryWire } from '../../api/performance-lab-api-types';

import { createPerformanceTestDetailPresentation } from '../performance-test-detail-presentation';
import { PerformanceTestDetailContainer } from '../performance-test-detail-container';

const mockFullEntry: PerformanceHistoryEntryWire = {
  session: {
    test_id: 'lac-101',
    performed_at: '2026-08-01T10:00:00+00:00',
    test_type: 'lactate_step_test',
    status: 'completed',
    modality: 'cycling',
    protocol_name: '3-min ramp',
    body_mass_kg: 72.0,
    ambient_temperature_c: 20.0,
    notes: 'Well rested',
    stages: [
      {
        stage_number: 1,
        duration_seconds: 180,
        power_watts: 150.0,
        speed_kph: null,
        heart_rate_bpm: 125,
        lactate_mmol_l: 1.2,
        cadence_rpm: 90.0,
        perceived_exertion: 3.0,
        completion_status: 'completed',
        notes: null,
      },
      {
        stage_number: 2,
        duration_seconds: 180,
        power_watts: 190.0,
        speed_kph: null,
        heart_rate_bpm: 142,
        lactate_mmol_l: 2.1,
        cadence_rpm: 92.0,
        perceived_exertion: 5.0,

        completion_status: 'completed',
        notes: null,
      },
    ],
  },
  lactate_curve: {
    test_id: 'lac-101',
    points: [
      {
        stage_number: 1,
        power_watts: 150.0,
        speed_kph: null,
        heart_rate_bpm: 125,
        lactate_mmol_l: 1.2,
        absolute_change_mmol_l: null,
        relative_change_percent: null,
      },
      {
        stage_number: 2,
        power_watts: 190.0,
        speed_kph: null,
        heart_rate_bpm: 142,
        lactate_mmol_l: 2.1,
        absolute_change_mmol_l: 0.9,
        relative_change_percent: 75.0,
      },
    ],
  },
  threshold_analysis: {
    test_id: 'lac-101',
    lt1: {
      name: 'LT1',
      status: 'detected',
      stage_number: 2,
      power_watts: 190.0,
      speed_kph: null,
      heart_rate_bpm: 142,
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

describe('createPerformanceTestDetailPresentation', () => {
  it('renders loading state', () => {
    const el = createPerformanceTestDetailPresentation({ state: { kind: 'loading' } });
    expect(el.querySelector('[role="status"]')).not.toBeNull();
  });

  it('renders not_found state', () => {
    const el = createPerformanceTestDetailPresentation({ state: { kind: 'not_found' } });
    expect(el.textContent).toContain('Nie znaleziono testu');
  });

  it('renders ready detail view with header, cards, chart, and stages table', () => {
    const onBack = vi.fn();
    const el = createPerformanceTestDetailPresentation({
      state: { kind: 'ready', entry: mockFullEntry },
      onBack,
    });

    expect(el.querySelector('.pl-detail__title')?.textContent).toContain('Test stopniowany');
    expect(el.textContent).toContain('LT1');
    expect(el.textContent).toContain('LT2');

    // Back button click
    const backBtn = el.querySelector<HTMLButtonElement>('.pl-detail__back-btn');
    expect(backBtn).not.toBeNull();
    backBtn?.click();
    expect(onBack).toHaveBeenCalledTimes(1);

    // SVG chart present
    const chart = el.querySelector('.pl-curve-chart');
    expect(chart).not.toBeNull();
    expect(chart?.getAttribute('role')).toBe('img');

    // LT1 marker exists (blue #38bdf8), LT2 not_reached does not create marker
    const circles = chart?.querySelectorAll('circle');
    // 2 data dots + 1 LT1 marker = 3 circles total
    expect(circles?.length).toBe(3);

    // Table rows
    const rows = el.querySelectorAll('.pl-detail__table tbody tr');
    expect(rows.length).toBe(2);
  });

  it('renders single-point lactate curve without division by zero NaN/Infinity', () => {
    const singlePointEntry: PerformanceHistoryEntryWire = {
      ...mockFullEntry,
      lactate_curve: {
        test_id: 'lac-101',
        points: [
          {
            stage_number: 1,
            power_watts: 150.0,
            speed_kph: null,
            heart_rate_bpm: 125,
            lactate_mmol_l: 1.2,
            absolute_change_mmol_l: null,
            relative_change_percent: null,
          },
        ],
      },
    };

    const el = createPerformanceTestDetailPresentation({
      state: { kind: 'ready', entry: singlePointEntry },
    });

    const svg = el.querySelector('.pl-curve-chart__svg');
    expect(svg).not.toBeNull();
    expect(svg?.innerHTML).not.toContain('NaN');
    expect(svg?.innerHTML).not.toContain('Infinity');
  });

  it('renders null metrics as dash placeholders and handles missing analysis/curve', () => {
    const nullEntry: PerformanceHistoryEntryWire = {
      session: {
        test_id: 'lac-null',
        performed_at: '2026-08-01T10:00:00+00:00',
        test_type: 'ftp_test',
        status: 'completed',
        modality: 'running',
        protocol_name: null,
        body_mass_kg: null,
        ambient_temperature_c: null,
        notes: null,
        stages: [
          {
            stage_number: 1,
            duration_seconds: null,
            power_watts: null,
            speed_kph: null,
            heart_rate_bpm: null,
            lactate_mmol_l: null,
            cadence_rpm: null,
            perceived_exertion: null,
            completion_status: 'completed',
            notes: null,
          },
        ],
      },
      lactate_curve: null,
      threshold_analysis: null,
    };

    const el = createPerformanceTestDetailPresentation({
      state: { kind: 'ready', entry: nullEntry },
    });

    expect(el.textContent).toContain('Masa ciała—');
    expect(el.textContent).toContain('Temp. otoczenia—');
    expect(el.querySelector('.pl-curve-chart')).toBeNull();
    expect(el.querySelector('.pl-detail__thresh-grid')).toBeNull();
  });
});


describe('PerformanceTestDetailContainer', () => {
  let rootEl: HTMLElement;

  beforeEach(() => {
    rootEl = document.createElement('div');
    document.body.appendChild(rootEl);
  });

  afterEach(() => {
    document.body.removeChild(rootEl);
  });

  it('fetches data and renders ready detail if testId matches', async () => {
    const stubClient = {
      getHistory: vi.fn().mockResolvedValue({
        success: true,
        data: { entries: [mockFullEntry] },
      }),
    };

    const container = new PerformanceTestDetailContainer(rootEl, stubClient as any, 'lac-101');
    await container.init();

    expect(rootEl.querySelector('.pl-detail__title')).not.toBeNull();
  });

  it('renders not_found if testId missing in history', async () => {
    const stubClient = {
      getHistory: vi.fn().mockResolvedValue({
        success: true,
        data: { entries: [mockFullEntry] },
      }),
    };

    const container = new PerformanceTestDetailContainer(rootEl, stubClient as any, 'missing-id');
    await container.init();

    expect(rootEl.textContent).toContain('Nie znaleziono testu');
  });
});
