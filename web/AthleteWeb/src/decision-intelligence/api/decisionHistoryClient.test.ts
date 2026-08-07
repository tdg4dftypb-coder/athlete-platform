import { describe, it, expect } from 'vitest';
import { parseDecisionHistoryPayloadV1 } from './decisionHistoryClient';
import type { DecisionAuditRecordWire } from './decision-intelligence-api-types';

const sampleRecord: DecisionAuditRecordWire = {
  decision_id: 'dec-hist-01',
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

describe('parseDecisionHistoryPayloadV1', () => {
  it('parses valid empty history', () => {
    const payload = {
      history: {
        records: [],
        count: 0,
      },
    };
    const res = parseDecisionHistoryPayloadV1(payload);
    expect(res.valid).toBe(true);
    expect(res.data).toEqual({ records: [], count: 0 });
  });

  it('parses valid history with records', () => {
    const payload = {
      history: {
        records: [sampleRecord],
        count: 1,
      },
    };
    const res = parseDecisionHistoryPayloadV1(payload);
    expect(res.valid).toBe(true);
    expect(res.data?.count).toBe(1);
    expect(res.data?.records.length).toBe(1);
  });

  it('rejects payload with extra root key', () => {
    const payload = {
      history: { records: [], count: 0 },
      extra: true,
    };
    const res = parseDecisionHistoryPayloadV1(payload);
    expect(res.valid).toBe(false);
    expect(res.error).toContain('Exact root keyset');
  });

  it('rejects payload when count does not match records length', () => {
    const payload = {
      history: {
        records: [sampleRecord],
        count: 5,
      },
    };
    const res = parseDecisionHistoryPayloadV1(payload);
    expect(res.valid).toBe(false);
    expect(res.error).toContain('count must match records.length');
  });
});
