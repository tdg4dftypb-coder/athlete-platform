import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { DecisionIntelligenceApiClient, validateDecisionAuditRecord } from '../decision-intelligence-api-client';
import type { DecisionAuditRecordWire } from '../decision-intelligence-api-types';

function buildValidRecordWire(): DecisionAuditRecordWire {
  return {
    decision_id: 'dec-001',
    recorded_at: '2026-08-06T08:00:00Z',
    context: {
      generated_at: '2026-08-06T08:00:00Z',
      recovery: {
        status: 'available',
        recovery_score: 85,
        recovery_status: 'ready',
        hrv_status: 'normal',
        resting_heart_rate_status: 'normal',
        sleep_status: 'good',
        generated_at: '2026-08-06T07:55:00Z',
      },
      training: {
        status: 'available',
        planned_session_type: 'endurance',
        planned_duration_minutes: 60,
        planned_intensity: 'moderate',
        recent_training_load: 350,
        fatigue_status: 'normal',
        generated_at: '2026-08-06T07:55:00Z',
      },
      biomarkers: {
        status: 'available',
        attention_count: 0,
        critical_count: 0,
        signals: [],
        generated_at: '2026-08-06T07:55:00Z',
      },
      performance: {
        status: 'available',
        latest_test_id: 'lac-01',
        latest_test_type: 'lactate_step_test',
        performed_at: '2026-08-01T10:00:00Z',
        lt1: null,
        lt2: null,
      },
    },
    policy_result: {
      generated_at: '2026-08-06T08:00:00Z',
      action: 'proceed',
      severity: 'low',
      signals: [
        { code: 'recovery_ready', source: 'recovery', severity: 'low', summary: 'Recovery ready' },
      ],
      confidence: 0.6,
      policy_version: '2.0',
    },
    recommendation_plan: {
      generated_at: '2026-08-06T08:00:00Z',
      action: 'proceed',
      severity: 'low',
      confidence: 0.6,
      policy_version: '2.0',
      recommendations: [
        {
          code: 'proceed_as_planned',
          category: 'training',
          priority: 'low',
          title: 'Proceed as planned',
          description: 'Desc',
          source_signal_codes: ['recovery_ready'],
        },
      ],
      explanation: {
        headline: 'Training can proceed',
        summary: 'Summary text',
        items: [
          { signal_code: 'recovery_ready', source: 'recovery', severity: 'low', summary: 'Recovery ready' },
        ],
      },
    },
  };
}

describe('validateDecisionAuditRecord', () => {
  it('validates a valid record', () => {
    const rec = buildValidRecordWire();
    const res = validateDecisionAuditRecord(rec);
    expect(res.valid).toBe(true);
    expect(res.data).toEqual(rec);
  });

  it('rejects invalid action or severity', () => {
    const rec = buildValidRecordWire();
    (rec.policy_result as any).action = 'invalid_action';
    expect(validateDecisionAuditRecord(rec).valid).toBe(false);
  });

  it('rejects mismatch in timestamps', () => {
    const rec = buildValidRecordWire();
    rec.context.generated_at = '2026-08-06T09:00:00Z';
    expect(validateDecisionAuditRecord(rec).valid).toBe(false);
  });

  it('rejects mismatch in explanation item and signal', () => {
    const rec = buildValidRecordWire();
    rec.recommendation_plan.explanation.items[0].signal_code = 'mismatched_code';
    expect(validateDecisionAuditRecord(rec).valid).toBe(false);
  });

  it('rejects whitespace-only decision_id', () => {
    const rec = buildValidRecordWire();
    rec.decision_id = '   ';
    expect(validateDecisionAuditRecord(rec).valid).toBe(false);
  });

  it('rejects out of range confidence', () => {
    const rec = buildValidRecordWire();
    (rec.policy_result as any).confidence = 1.5;
    expect(validateDecisionAuditRecord(rec).valid).toBe(false);

    const rec2 = buildValidRecordWire();
    (rec2.policy_result as any).confidence = -0.1;
    expect(validateDecisionAuditRecord(rec2).valid).toBe(false);
  });

});

describe('DecisionIntelligenceApiClient', () => {
  let fetchSpy: any;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch');
  });


  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it('returns data: null when backend returns { decision: null }', async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ decision: null }),
    } as Response);

    const client = new DecisionIntelligenceApiClient('/api/v1/decision-intelligence');
    const result = await client.getLatestRecord();
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toBeNull();
    }
  });

  it('returns valid record when backend returns HTTP 200 with record', async () => {
    const record = buildValidRecordWire();
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ decision: record }),
    } as Response);

    const client = new DecisionIntelligenceApiClient();
    const result = await client.getLatestRecord();
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toEqual(record);
    }
  });

  it('handles HTTP 503 as server_unavailable', async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 503,
    } as Response);

    const client = new DecisionIntelligenceApiClient();
    const result = await client.getLatestRecord();
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('server_unavailable');
    }
  });

  it('handles invalid JSON payload as invalid_data', async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => { throw new Error('Bad JSON'); },
    } as unknown as Response);

    const client = new DecisionIntelligenceApiClient();

    const result = await client.getLatestRecord();
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('invalid_data');
    }
  });

  it('handles HTTP 404 / 500 as server_error', async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response);

    const client = new DecisionIntelligenceApiClient();
    const result = await client.getLatestRecord();
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('server_error');
    }
  });

});
