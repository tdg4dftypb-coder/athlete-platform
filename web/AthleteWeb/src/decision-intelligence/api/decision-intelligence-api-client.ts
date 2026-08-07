import type {
  DecisionIntelligenceApiResponseWire,
  DecisionAuditRecordWire,
  DecisionValidationResult,
} from './decision-intelligence-api-types';


export type DecisionIntelligenceApiErrorType =
  | 'server_unavailable'
  | 'server_error'
  | 'network_error'
  | 'timeout'
  | 'invalid_data';

export interface DecisionIntelligenceApiError {
  type: DecisionIntelligenceApiErrorType;
  message: string;
}

export type DecisionIntelligenceApiResult =
  | { success: true; data: DecisionAuditRecordWire | null }
  | { success: false; error: DecisionIntelligenceApiError };

const ALLOWED_ACTIONS: ReadonlySet<string> = new Set([
  'proceed',
  'reduce',
  'replace_with_recovery',
  'rest',
  'review',
]);

const ALLOWED_SEVERITIES: ReadonlySet<string> = new Set(['low', 'medium', 'high', 'critical']);

const ALLOWED_STATUSES: ReadonlySet<string> = new Set([
  'available',
  'partial',
  'unavailable',
  'stale',
]);

const ALLOWED_CATEGORIES: ReadonlySet<string> = new Set([
  'training',
  'recovery',
  'laboratory',
  'data_quality',
  'performance',
]);

const ALLOWED_PRIORITIES: ReadonlySet<string> = new Set(['low', 'medium', 'high', 'critical']);

function isNonEmptyString(val: unknown): val is string {
  return typeof val === 'string' && val.trim().length > 0;
}

function isValidIsoDate(val: unknown): boolean {
  if (typeof val !== 'string' || val.trim().length === 0) return false;
  const parsed = Date.parse(val);
  return !isNaN(parsed);
}

export function validateDecisionAuditRecord(
  raw: unknown
): DecisionValidationResult<DecisionAuditRecordWire> {
  if (typeof raw !== 'object' || raw === null) {
    return { valid: false, error: 'Record must be non-null object' };
  }

  const rec = raw as Record<string, unknown>;

  if (!isNonEmptyString(rec.decision_id)) {
    return { valid: false, error: 'Invalid decision_id' };
  }
  if (!isValidIsoDate(rec.recorded_at)) {
    return { valid: false, error: 'Invalid recorded_at' };
  }

  // 1. Validate Context
  if (typeof rec.context !== 'object' || rec.context === null) {
    return { valid: false, error: 'Invalid context' };
  }
  const ctx = rec.context as Record<string, unknown>;
  if (!isValidIsoDate(ctx.generated_at)) {
    return { valid: false, error: 'Invalid context generated_at' };
  }

  // Recovery
  if (typeof ctx.recovery !== 'object' || ctx.recovery === null) {
    return { valid: false, error: 'Invalid recovery context' };
  }
  const recov = ctx.recovery as Record<string, unknown>;
  if (typeof recov.status !== 'string' || !ALLOWED_STATUSES.has(recov.status)) {
    return { valid: false, error: 'Invalid recovery status' };
  }

  // Training
  if (typeof ctx.training !== 'object' || ctx.training === null) {
    return { valid: false, error: 'Invalid training context' };
  }
  const tr = ctx.training as Record<string, unknown>;
  if (typeof tr.status !== 'string' || !ALLOWED_STATUSES.has(tr.status)) {
    return { valid: false, error: 'Invalid training status' };
  }

  // Biomarkers
  if (typeof ctx.biomarkers !== 'object' || ctx.biomarkers === null) {
    return { valid: false, error: 'Invalid biomarkers context' };
  }
  const bio = ctx.biomarkers as Record<string, unknown>;
  if (typeof bio.status !== 'string' || !ALLOWED_STATUSES.has(bio.status)) {
    return { valid: false, error: 'Invalid biomarkers status' };
  }
  if (typeof bio.attention_count !== 'number' || typeof bio.critical_count !== 'number') {
    return { valid: false, error: 'Invalid biomarker counts' };
  }
  if (!Array.isArray(bio.signals)) {
    return { valid: false, error: 'Biomarker signals must be array' };
  }

  // Performance
  if (typeof ctx.performance !== 'object' || ctx.performance === null) {
    return { valid: false, error: 'Invalid performance context' };
  }
  const perf = ctx.performance as Record<string, unknown>;
  if (typeof perf.status !== 'string' || !ALLOWED_STATUSES.has(perf.status)) {
    return { valid: false, error: 'Invalid performance status' };
  }

  // 2. Validate Policy Result
  if (typeof rec.policy_result !== 'object' || rec.policy_result === null) {
    return { valid: false, error: 'Invalid policy_result' };
  }
  const pol = rec.policy_result as Record<string, unknown>;
  if (!isValidIsoDate(pol.generated_at)) {
    return { valid: false, error: 'Invalid policy_result generated_at' };
  }
  if (typeof pol.action !== 'string' || !ALLOWED_ACTIONS.has(pol.action)) {
    return { valid: false, error: 'Invalid policy action' };
  }
  if (typeof pol.severity !== 'string' || !ALLOWED_SEVERITIES.has(pol.severity)) {
    return { valid: false, error: 'Invalid policy severity' };
  }
  if (typeof pol.confidence !== 'number' || pol.confidence < 0 || pol.confidence > 1) {
    return { valid: false, error: 'Invalid policy confidence' };
  }
  if (!isNonEmptyString(pol.policy_version)) {
    return { valid: false, error: 'Invalid policy_version' };
  }
  if (!Array.isArray(pol.signals)) {
    return { valid: false, error: 'Policy signals must be array' };
  }

  // 3. Validate Recommendation Plan
  if (typeof rec.recommendation_plan !== 'object' || rec.recommendation_plan === null) {
    return { valid: false, error: 'Invalid recommendation_plan' };
  }
  const plan = rec.recommendation_plan as Record<string, unknown>;
  if (!isValidIsoDate(plan.generated_at)) {
    return { valid: false, error: 'Invalid plan generated_at' };
  }
  if (typeof plan.action !== 'string' || !ALLOWED_ACTIONS.has(plan.action)) {
    return { valid: false, error: 'Invalid plan action' };
  }
  if (typeof plan.severity !== 'string' || !ALLOWED_SEVERITIES.has(plan.severity)) {
    return { valid: false, error: 'Invalid plan severity' };
  }
  if (typeof plan.confidence !== 'number' || plan.confidence < 0 || plan.confidence > 1) {
    return { valid: false, error: 'Invalid plan confidence' };
  }
  if (!isNonEmptyString(plan.policy_version)) {
    return { valid: false, error: 'Invalid plan policy_version' };
  }
  if (!Array.isArray(plan.recommendations) || plan.recommendations.length === 0) {
    return { valid: false, error: 'Recommendations must be non-empty array' };
  }

  for (const r of plan.recommendations) {
    if (typeof r !== 'object' || r === null) return { valid: false, error: 'Invalid recommendation' };
    const recObj = r as Record<string, unknown>;
    if (!isNonEmptyString(recObj.code) || !isNonEmptyString(recObj.title) || !isNonEmptyString(recObj.description)) {
      return { valid: false, error: 'Invalid recommendation text fields' };
    }
    if (typeof recObj.category !== 'string' || !ALLOWED_CATEGORIES.has(recObj.category)) {
      return { valid: false, error: 'Invalid recommendation category' };
    }
    if (typeof recObj.priority !== 'string' || !ALLOWED_PRIORITIES.has(recObj.priority)) {
      return { valid: false, error: 'Invalid recommendation priority' };
    }
    if (!Array.isArray(recObj.source_signal_codes)) {
      return { valid: false, error: 'source_signal_codes must be array' };
    }
  }

  // Explanation
  if (typeof plan.explanation !== 'object' || plan.explanation === null) {
    return { valid: false, error: 'Invalid explanation' };
  }
  const exp = plan.explanation as Record<string, unknown>;
  if (!isNonEmptyString(exp.headline) || !isNonEmptyString(exp.summary)) {
    return { valid: false, error: 'Invalid explanation headline or summary' };
  }
  if (!Array.isArray(exp.items) || exp.items.length === 0) {
    return { valid: false, error: 'Explanation items must be non-empty array' };
  }

  for (const item of exp.items) {
    if (typeof item !== 'object' || item === null) return { valid: false, error: 'Invalid explanation item' };
    const itemObj = item as Record<string, unknown>;
    if (!isNonEmptyString(itemObj.signal_code) || !isNonEmptyString(itemObj.source) || !isNonEmptyString(itemObj.summary)) {
      return { valid: false, error: 'Invalid explanation item text fields' };
    }
    if (typeof itemObj.severity !== 'string' || !ALLOWED_SEVERITIES.has(itemObj.severity)) {
      return { valid: false, error: 'Invalid explanation item severity' };
    }
  }

  // 4. Cross-Field Consistency Validation
  if (ctx.generated_at !== pol.generated_at) {
    return { valid: false, error: 'Mismatch context/policy generated_at' };
  }
  if (pol.generated_at !== plan.generated_at) {
    return { valid: false, error: 'Mismatch policy/plan generated_at' };
  }
  if (pol.action !== plan.action) {
    return { valid: false, error: 'Mismatch policy/plan action' };
  }
  if (pol.severity !== plan.severity) {
    return { valid: false, error: 'Mismatch policy/plan severity' };
  }
  if (pol.confidence !== plan.confidence) {
    return { valid: false, error: 'Mismatch policy/plan confidence' };
  }
  if (pol.policy_version !== plan.policy_version) {
    return { valid: false, error: 'Mismatch policy/plan policy_version' };
  }

  const polSignals = pol.signals as Array<Record<string, unknown>>;
  const expItems = exp.items as Array<Record<string, unknown>>;
  if (expItems.length !== polSignals.length) {
    return { valid: false, error: 'Mismatch explanation items count and policy signals count' };
  }

  for (let i = 0; i < polSignals.length; i++) {
    if (expItems[i].signal_code !== polSignals[i].code) {
      return { valid: false, error: `Mismatch signal_code at index ${i}` };
    }
    if (expItems[i].source !== polSignals[i].source) {
      return { valid: false, error: `Mismatch source at index ${i}` };
    }
    if (expItems[i].severity !== polSignals[i].severity) {
      return { valid: false, error: `Mismatch severity at index ${i}` };
    }
    if (expItems[i].summary !== polSignals[i].summary) {
      return { valid: false, error: `Mismatch summary at index ${i}` };
    }
  }

  return { valid: true, data: raw as DecisionAuditRecordWire };
}

export class DecisionIntelligenceApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(baseUrl = '/api/v1/decision-intelligence', timeoutMs = 8000) {
    this.baseUrl = baseUrl;
    this.timeoutMs = timeoutMs;
  }

  async getLatestRecord(): Promise<DecisionIntelligenceApiResult> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(`${this.baseUrl}/latest`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (response.status === 503) {
        return {
          success: false,
          error: {
            type: 'server_unavailable',
            message: 'Usługa Decision Intelligence jest tymczasowo niedostępna.',
          },
        };
      }

      if (!response.ok) {
        return {
          success: false,
          error: {
            type: 'server_error',
            message: `Błąd serwera (HTTP ${response.status}).`,
          },
        };
      }

      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        return {
          success: false,
          error: {
            type: 'invalid_data',
            message: 'Błąd sparsowania odpowiedzi JSON z serwera.',
          },
        };
      }

      if (typeof payload !== 'object' || payload === null || !('decision' in payload)) {
        return {
          success: false,
          error: {
            type: 'invalid_data',
            message: 'Odpowiedź serwera nie zawiera pola decision.',
          },
        };
      }

      const resWire = payload as DecisionIntelligenceApiResponseWire;
      if (resWire.decision === null) {
        return { success: true, data: null };
      }

      const validation = validateDecisionAuditRecord(resWire.decision);
      if (!validation.valid || !validation.data) {
        return {
          success: false,
          error: {
            type: 'invalid_data',
            message: validation.error ?? 'Nieprawidłowa struktura rekordu audytowego.',
          },
        };
      }

      return { success: true, data: validation.data };

    } catch (err: unknown) {
      clearTimeout(timer);
      if (err instanceof Error && err.name === 'AbortError') {
        return {
          success: false,
          error: {
            type: 'timeout',
            message: 'Upłynął limit czasu żądania.',
          },
        };
      }
      return {
        success: false,
        error: {
          type: 'network_error',
          message: 'Błąd połączenia z serwerem.',
        },
      };
    }
  }
}
