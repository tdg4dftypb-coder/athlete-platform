import { describe, it, expect, vi } from 'vitest';
import { createDecisionHistoryPresentation } from './decisionHistoryPresentation';
import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';


const sampleRecord: DecisionAuditRecordWire = {
  decision_id: 'dec-pres-01',
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
    recommendations: [{ code: 'REC_01', category: 'training', priority: 'low', title: 'Train hard', description: 'Complete planned session', source_signal_codes: ['SIG_01'] }],
    explanation: {
      headline: 'Proceed as planned',
      summary: 'Summary text',
      items: [{ signal_code: 'SIG_01', source: 'recovery', severity: 'low', summary: 'All good' }],
    },
  },
};

describe('createDecisionHistoryPresentation', () => {
  it('renders loading state', () => {
    const el = createDecisionHistoryPresentation({ kind: 'loading' }, () => {});
    expect(el.querySelector('.decision-history-loading')).not.toBeNull();
    expect(el.textContent).toContain('Wczytywanie historii decyzji...');
  });

  it('renders empty state', () => {
    const el = createDecisionHistoryPresentation({ kind: 'empty' }, () => {});
    expect(el.querySelector('.decision-history-empty')).not.toBeNull();
    expect(el.textContent).toContain('Brak zapisanych decyzji');
  });

  it('renders ready state with reversed UI order', () => {
    const onRefresh = vi.fn();
    const rec2 = { ...sampleRecord, decision_id: 'dec-pres-02', context: { ...sampleRecord.context, generated_at: '2026-08-06T21:00:00.000Z' } };

    const el = createDecisionHistoryPresentation(
      {
        kind: 'ready',
        payload: {
          records: [sampleRecord, rec2],
          count: 2,
        },
      },
      onRefresh
    );

    expect(el.textContent).toContain('2 decyzji');
    const items = el.querySelectorAll('.decision-history-item');
    expect(items.length).toBe(2);

    // UI order should present newest first (rec2)
    expect(items[0].textContent).toContain('ID decyzji: dec-pres-02');
    expect(items[1].textContent).toContain('ID decyzji: dec-pres-01');
    expect(items[0].textContent).toContain('Kontynuuj zgodnie z planem');
    expect(items[0].textContent).toContain('Pewność: 95%');
    expect(items[0].textContent).toContain('Niska');
  });


  it('triggers refresh callback on button click', () => {
    const onRefresh = vi.fn();
    const el = createDecisionHistoryPresentation({ kind: 'empty' }, onRefresh);

    const btn = el.querySelector('.btn-refresh-history') as HTMLButtonElement;
    btn.click();

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
