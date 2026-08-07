import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { DecisionHistoryContainer } from './decisionHistoryContainer';
import * as historyClient from '../api/decisionHistoryClient';

import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';

const sampleRecord: DecisionAuditRecordWire = {
  decision_id: 'dec-cont-01',
  recorded_at: '2026-08-06T20:00:00.000Z',
  context: {
    generated_at: '2026-08-06T20:00:00.000Z',
    recovery: { status: 'available', recovery_score: 85, recovery_status: 'ready', hrv_status: null, resting_heart_rate_status: null, sleep_status: null, generated_at: null },
    training: { status: 'available', planned_session_type: 'endurance', planned_duration_minutes: 60, planned_intensity: 'moderate', recent_training_load: null, fatigue_status: null, generated_at: null },
    biomarkers: { status: 'available', attention_count: 0, critical_count: 0, signals: [], generated_at: null },
    performance: { status: 'unavailable', latest_test_id: null, latest_test_type: null, performed_at: null, lt1: null, lt2: null },
  },
  policy_result: {
    generated_at: '2026-08-06T20:00:00.000Z',
    action: 'proceed',
    severity: 'low',
    signals: [{ code: 'SIG_01', source: 'recovery', severity: 'low', summary: 'All good' }],
    confidence: 0.95,
    policy_version: '2.0',
  },
  recommendation_plan: {
    generated_at: '2026-08-06T20:00:00.000Z',
    action: 'proceed',
    severity: 'low',
    confidence: 0.95,
    policy_version: '2.0',
    recommendations: [{ code: 'REC_01', category: 'training', priority: 'low', title: 'Train', description: 'Go train', source_signal_codes: ['SIG_01'] }],
    explanation: {
      headline: 'Proceed as planned',
      summary: 'Summary text',
      items: [{ signal_code: 'SIG_01', source: 'recovery', severity: 'low', summary: 'All good' }],
    },
  },
};

describe('DecisionHistoryContainer', () => {
  let rootEl: HTMLElement;

  beforeEach(() => {
    rootEl = document.createElement('div');
    document.body.appendChild(rootEl);
  });

  afterEach(() => {
    document.body.removeChild(rootEl);
    vi.restoreAllMocks();
  });

  it('renders loading state then ready state with records', async () => {
    vi.spyOn(historyClient, 'fetchDecisionHistory').mockResolvedValueOnce({
      success: true,
      data: {
        records: [sampleRecord],
        count: 1,
      },
    });

    const container = new DecisionHistoryContainer(rootEl);
    await container.init();

    expect(rootEl.textContent).toContain('Historia decyzji');
    expect(rootEl.textContent).toContain('Kontynuuj zgodnie z planem');
    expect(rootEl.textContent).toContain('1 decyzja');
  });


  it('renders empty state when history has no records', async () => {
    vi.spyOn(historyClient, 'fetchDecisionHistory').mockResolvedValueOnce({
      success: true,
      data: {
        records: [],
        count: 0,
      },
    });

    const container = new DecisionHistoryContainer(rootEl);
    await container.init();

    expect(rootEl.textContent).toContain('Brak zapisanych decyzji');
  });

  it('renders error state on fetch failure', async () => {
    vi.spyOn(historyClient, 'fetchDecisionHistory').mockResolvedValueOnce({
      success: false,
      error: {
        type: 'network_error',
        message: 'Błąd połączenia z serwerem.',
      },
    });

    const container = new DecisionHistoryContainer(rootEl);
    await container.init();

    expect(rootEl.textContent).toContain('Brak połączenia z serwerem.');
  });
});
