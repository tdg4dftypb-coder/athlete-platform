import { describe, it, expect, vi } from 'vitest';
import { createDecisionIntelligencePresentation } from '../decision-intelligence-presentation';
import { DecisionIntelligenceContainer } from '../decision-intelligence-container';
import type { DecisionIntelligenceApiClient } from '../../api/decision-intelligence-api-client';
import type { DecisionAuditRecordWire } from '../../api/decision-intelligence-api-types';

function buildStubRecord(): DecisionAuditRecordWire {
  return {
    decision_id: 'dec-ui-01',
    recorded_at: '2026-08-06T08:00:00Z',
    context: {
      generated_at: '2026-08-06T08:00:00Z',
      recovery: {
        status: 'available',
        recovery_score: 50,
        recovery_status: 'moderate',
        hrv_status: 'normal',
        resting_heart_rate_status: 'normal',
        sleep_status: 'good',
        generated_at: '2026-08-06T07:55:00Z',
      },
      training: {
        status: 'available',
        planned_session_type: 'intervals',
        planned_duration_minutes: 60,
        planned_intensity: 'high',
        recent_training_load: 400,
        fatigue_status: 'high',
        generated_at: '2026-08-06T07:55:00Z',
      },
      biomarkers: {
        status: 'available',
        attention_count: 1,
        critical_count: 0,
        signals: [{ canonical_code: 'FERRITIN', interpretation: 'ATTENTION', confidence: 'HIGH', summary: 'Ferritin low' }],
        generated_at: '2026-08-06T07:55:00Z',
      },
      performance: {
        status: 'available',
        latest_test_id: 'lac-100',
        latest_test_type: 'lactate_step_test',
        performed_at: '2026-08-01T10:00:00Z',
        lt1: { name: 'LT1', status: 'DETECTED', power_watts: 200, speed_kph: null, heart_rate_bpm: 145, lactate_mmol_l: 2.0, confidence: 0.8, method: 'fixed_2_mmol' },
        lt2: { name: 'LT2', status: 'DETECTED', power_watts: 280, speed_kph: null, heart_rate_bpm: 172, lactate_mmol_l: 4.0, confidence: 0.8, method: 'fixed_4_mmol' },
      },
    },
    policy_result: {
      generated_at: '2026-08-06T08:00:00Z',
      action: 'replace_with_recovery',
      severity: 'high',
      signals: [
        { code: 'recovery_low', source: 'recovery', severity: 'high', summary: 'Low recovery' },
        { code: 'biomarker_attention', source: 'biomarkers', severity: 'high', summary: 'Ferritin requires attention' },
      ],
      confidence: 0.85,
      policy_version: '2.0',
    },
    recommendation_plan: {
      generated_at: '2026-08-06T08:00:00Z',
      action: 'replace_with_recovery',
      severity: 'high',
      confidence: 0.85,
      policy_version: '2.0',
      recommendations: [
        {
          code: 'replace_with_recovery',
          category: 'recovery',
          priority: 'high',
          title: 'Replace with recovery',
          description: 'Replace intervals with light active recovery.',
          source_signal_codes: ['recovery_low'],
        },
        {
          code: 'review_laboratory_signals',
          category: 'laboratory',
          priority: 'high',
          title: 'Review laboratory signals',
          description: 'Check ferritin level.',
          source_signal_codes: ['biomarker_attention'],
        },
      ],
      explanation: {
        headline: 'Recovery should replace the planned session',
        summary: 'Signals indicate elevated fatigue.',
        items: [
          { signal_code: 'recovery_low', source: 'recovery', severity: 'high', summary: 'Low recovery' },
          { signal_code: 'biomarker_attention', source: 'biomarkers', severity: 'high', summary: 'Ferritin requires attention' },
        ],
      },
    },
  };
}

describe('DecisionIntelligencePresentation', () => {
  it('renders loading skeleton', () => {
    const el = createDecisionIntelligencePresentation({ kind: 'loading' }, () => {}, () => {});
    expect(el.querySelector('.decision-loading-skeleton')).not.toBeNull();
    expect(el.querySelector('[role="status"]')).not.toBeNull();
  });

  it('renders empty state when decision is null', () => {
    const el = createDecisionIntelligencePresentation({ kind: 'empty' }, () => {}, () => {});
    expect(el.textContent).toContain('No decision is available yet');
  });

  it('renders ready decision view with action, recommendations, explanation and context', () => {
    const record = buildStubRecord();
    const el = createDecisionIntelligencePresentation({ kind: 'ready', record }, () => {}, () => {});

    expect(el.querySelector('h1')?.textContent).toBe('AI Coach');
    expect(el.querySelectorAll('h1').length).toBe(1);

    // Hero Action
    expect(el.querySelector('.decision-hero-action')?.textContent).toBe('Replace with recovery');
    expect(el.querySelector('.severity-badge')?.textContent).toBe('HIGH');
    expect(el.querySelector('.confidence-badge')?.textContent).toBe('85% Confidence');

    // Recommendations
    const recCards = el.querySelectorAll('.recommendation-card');
    expect(recCards.length).toBe(2);
    expect(recCards[0].textContent).toContain('Replace with recovery');

    // Explanation
    expect(el.querySelector('.explanation-headline')?.textContent).toBe('Recovery should replace the planned session');
    const expItems = el.querySelectorAll('.explanation-item');
    expect(expItems.length).toBe(2);

    // Context Grid
    const sourceCards = el.querySelectorAll('.context-source-card');
    expect(sourceCards.length).toBe(4);
    expect(el.textContent).toContain('LT1 Threshold');
    expect(el.textContent).toContain('200W');
  });

  it('renders error state with retry button', () => {
    const onRetry = vi.fn();
    const el = createDecisionIntelligencePresentation({ kind: 'failure', message: 'Custom error' }, onRetry, () => {});

    expect(el.querySelector('[role="alert"]')).not.toBeNull();
    const retryBtn = el.querySelector<HTMLButtonElement>('.btn-retry');
    expect(retryBtn).not.toBeNull();
    retryBtn?.click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders invalid_data error state safely without rendering raw payload', () => {
    const el = createDecisionIntelligencePresentation({ kind: 'invalid_data' }, () => {}, () => {});
    expect(el.querySelector('[role="alert"]')).not.toBeNull();
    expect(el.textContent).toContain('Decision data could not be loaded');
  });

  it('renders correct text headline for all 5 DecisionActions', () => {
    const actionsMap: Record<string, string> = {
      proceed: 'Proceed as planned',
      reduce: 'Reduce training load',
      replace_with_recovery: 'Replace with recovery',
      rest: 'Prioritize rest',
      review: 'Review before training',
    };

    for (const [action, expectedText] of Object.entries(actionsMap)) {
      const rec = buildStubRecord();
      rec.recommendation_plan.action = action as any;
      const el = createDecisionIntelligencePresentation({ kind: 'ready', record: rec }, () => {}, () => {});
      expect(el.querySelector('.decision-hero-action')?.textContent).toBe(expectedText);
    }
  });
});

describe('DecisionIntelligenceContainer', () => {
  it('fetches record and renders ready state', async () => {
    const record = buildStubRecord();
    const clientStub = {
      getLatestRecord: vi.fn().mockResolvedValue({ success: true, data: record }),
    } as unknown as DecisionIntelligenceApiClient;

    const rootEl = document.createElement('div');
    const container = new DecisionIntelligenceContainer(rootEl, clientStub);
    await container.init();

    expect(clientStub.getLatestRecord).toHaveBeenCalledTimes(1);
    expect(rootEl.querySelector('.decision-hero-action')?.textContent).toBe('Replace with recovery');
  });

  it('handles latest failure independently without failing history slot', async () => {
    const clientStub = {
      getLatestRecord: vi.fn().mockResolvedValue({
        success: false,
        error: { type: 'network_error', message: 'Błąd połączenia' },
      }),
    } as unknown as DecisionIntelligenceApiClient;

    const rootEl = document.createElement('div');
    const container = new DecisionIntelligenceContainer(rootEl, clientStub);
    await container.init();

    expect(clientStub.getLatestRecord).toHaveBeenCalledTimes(1);
    expect(rootEl.querySelector('.decision-error-state')).not.toBeNull();
    expect(rootEl.querySelector('#decision-history-slot')).not.toBeNull();
  });
});
