import type {
  PerformanceTestHistoryWire,
  PerformanceHistoryEntryWire,
  PerformanceTestSessionWire,
  PerformanceStageWire,
  LactateCurveWire,
  LactateCurvePointWire,
  LactateThresholdAnalysisWire,
  DetectedThresholdWire,
  PerformanceTestTypeWire,
  PerformanceTestStatusWire,
  ExerciseModalityWire,
  StageCompletionStatusWire,
  ThresholdDetectionStatusWire,
  PerformanceLabValidationResult,
} from './performance-lab-api-types';

export type PerformanceLabApiErrorType =
  | 'server_unavailable'
  | 'server_error'
  | 'network_error'
  | 'timeout'
  | 'invalid_data';

export interface PerformanceLabApiError {
  type: PerformanceLabApiErrorType;
  message: string;
}

export type PerformanceLabApiResult =
  | { success: true; data: PerformanceTestHistoryWire }
  | { success: false; error: PerformanceLabApiError };

// ── Allowed Enums Sets ────────────────────────────────────────────────────────

const ALLOWED_TEST_TYPES: ReadonlySet<string> = new Set([
  'lactate_step_test',
  'cardiopulmonary_exercise_test',
  'ftp_test',
  'field_test',
]);

const ALLOWED_TEST_STATUSES: ReadonlySet<string> = new Set([
  'planned',
  'completed',
  'partial',
  'invalid',
]);

const ALLOWED_MODALITIES: ReadonlySet<string> = new Set([
  'cycling',
  'running',
  'rowing',
  'other',
]);

const ALLOWED_STAGE_STATUSES: ReadonlySet<string> = new Set([
  'completed',
  'incomplete',
  'skipped',
]);

const ALLOWED_THRESHOLD_STATUSES: ReadonlySet<string> = new Set([
  'detected',
  'insufficient_data',
  'not_reached',
  'invalid_curve',
]);

// ── Validation Helpers ────────────────────────────────────────────────────────

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null;
}

function isNullableNumber(v: unknown): boolean {
  return v === null || typeof v === 'number';
}

function isNullableString(v: unknown): boolean {
  return v === null || typeof v === 'string';
}

// ── Recursive Validators ──────────────────────────────────────────────────────

function validateDetectedThreshold(raw: unknown, name: string): DetectedThresholdWire | null {
  if (!isObject(raw)) return null;
  if (raw['name'] !== name) return null;
  if (typeof raw['status'] !== 'string' || !ALLOWED_THRESHOLD_STATUSES.has(raw['status'])) return null;
  if (!isNullableNumber(raw['stage_number'])) return null;
  if (!isNullableNumber(raw['power_watts'])) return null;
  if (!isNullableNumber(raw['speed_kph'])) return null;
  if (!isNullableNumber(raw['heart_rate_bpm'])) return null;
  if (!isNullableNumber(raw['lactate_mmol_l'])) return null;
  if (typeof raw['target_lactate_mmol_l'] !== 'number') return null;
  if (!isNullableNumber(raw['confidence'])) return null;
  if (typeof raw['method'] !== 'string') return null;

  return {
    name: raw['name'] as string,
    status: raw['status'] as ThresholdDetectionStatusWire,
    stage_number: raw['stage_number'] as number | null,
    power_watts: raw['power_watts'] as number | null,
    speed_kph: raw['speed_kph'] as number | null,
    heart_rate_bpm: raw['heart_rate_bpm'] as number | null,
    lactate_mmol_l: raw['lactate_mmol_l'] as number | null,
    target_lactate_mmol_l: raw['target_lactate_mmol_l'] as number,
    confidence: raw['confidence'] as number | null,
    method: raw['method'] as string,
  };
}

function validateThresholdAnalysis(raw: unknown, expectedTestId: string): LactateThresholdAnalysisWire | null {
  if (!isObject(raw)) return null;
  if (raw['test_id'] !== expectedTestId) return null;

  const lt1 = validateDetectedThreshold(raw['lt1'], 'LT1');
  const lt2 = validateDetectedThreshold(raw['lt2'], 'LT2');
  if (!lt1 || !lt2) return null;

  return {
    test_id: raw['test_id'] as string,
    lt1,
    lt2,
  };
}

function validateCurvePoint(raw: unknown): LactateCurvePointWire | null {
  if (!isObject(raw)) return null;
  if (typeof raw['stage_number'] !== 'number') return null;
  if (!isNullableNumber(raw['power_watts'])) return null;
  if (!isNullableNumber(raw['speed_kph'])) return null;
  if (!isNullableNumber(raw['heart_rate_bpm'])) return null;
  if (typeof raw['lactate_mmol_l'] !== 'number') return null;
  if (!isNullableNumber(raw['absolute_change_mmol_l'])) return null;
  if (!isNullableNumber(raw['relative_change_percent'])) return null;

  return {
    stage_number: raw['stage_number'] as number,
    power_watts: raw['power_watts'] as number | null,
    speed_kph: raw['speed_kph'] as number | null,
    heart_rate_bpm: raw['heart_rate_bpm'] as number | null,
    lactate_mmol_l: raw['lactate_mmol_l'] as number,
    absolute_change_mmol_l: raw['absolute_change_mmol_l'] as number | null,
    relative_change_percent: raw['relative_change_percent'] as number | null,
  };
}

function validateLactateCurve(raw: unknown, expectedTestId: string): LactateCurveWire | null {
  if (!isObject(raw)) return null;
  if (raw['test_id'] !== expectedTestId) return null;
  if (!Array.isArray(raw['points'])) return null;

  const points: LactateCurvePointWire[] = [];
  for (const pt of raw['points'] as unknown[]) {
    const validatedPt = validateCurvePoint(pt);
    if (!validatedPt) return null;
    points.push(validatedPt);
  }

  return {
    test_id: raw['test_id'] as string,
    points,
  };
}

function validateStage(raw: unknown): PerformanceStageWire | null {
  if (!isObject(raw)) return null;
  if (typeof raw['stage_number'] !== 'number') return null;
  if (!isNullableNumber(raw['duration_seconds'])) return null;
  if (!isNullableNumber(raw['power_watts'])) return null;
  if (!isNullableNumber(raw['speed_kph'])) return null;
  if (!isNullableNumber(raw['heart_rate_bpm'])) return null;
  if (!isNullableNumber(raw['lactate_mmol_l'])) return null;
  if (!isNullableNumber(raw['cadence_rpm'])) return null;
  if (!isNullableNumber(raw['perceived_exertion'])) return null;
  if (typeof raw['completion_status'] !== 'string' || !ALLOWED_STAGE_STATUSES.has(raw['completion_status'])) return null;
  if (!isNullableString(raw['notes'])) return null;

  return {
    stage_number: raw['stage_number'] as number,
    duration_seconds: raw['duration_seconds'] as number | null,
    power_watts: raw['power_watts'] as number | null,
    speed_kph: raw['speed_kph'] as number | null,
    heart_rate_bpm: raw['heart_rate_bpm'] as number | null,
    lactate_mmol_l: raw['lactate_mmol_l'] as number | null,
    cadence_rpm: raw['cadence_rpm'] as number | null,
    perceived_exertion: raw['perceived_exertion'] as number | null,
    completion_status: raw['completion_status'] as StageCompletionStatusWire,
    notes: raw['notes'] as string | null,
  };
}

function validateSession(raw: unknown): PerformanceTestSessionWire | null {
  if (!isObject(raw)) return null;
  if (typeof raw['test_id'] !== 'string' || raw['test_id'] === '') return null;
  if (typeof raw['performed_at'] !== 'string' || raw['performed_at'] === '') return null;
  if (typeof raw['test_type'] !== 'string' || !ALLOWED_TEST_TYPES.has(raw['test_type'])) return null;
  if (typeof raw['status'] !== 'string' || !ALLOWED_TEST_STATUSES.has(raw['status'])) return null;
  if (typeof raw['modality'] !== 'string' || !ALLOWED_MODALITIES.has(raw['modality'])) return null;
  if (!isNullableString(raw['protocol_name'])) return null;
  if (!isNullableNumber(raw['body_mass_kg'])) return null;
  if (!isNullableNumber(raw['ambient_temperature_c'])) return null;
  if (!isNullableString(raw['notes'])) return null;

  if (!Array.isArray(raw['stages'])) return null;
  const stages: PerformanceStageWire[] = [];
  for (const st of raw['stages'] as unknown[]) {
    const validatedStage = validateStage(st);
    if (!validatedStage) return null;
    stages.push(validatedStage);
  }

  return {
    test_id: raw['test_id'] as string,
    performed_at: raw['performed_at'] as string,
    test_type: raw['test_type'] as PerformanceTestTypeWire,
    status: raw['status'] as PerformanceTestStatusWire,
    modality: raw['modality'] as ExerciseModalityWire,
    protocol_name: raw['protocol_name'] as string | null,
    body_mass_kg: raw['body_mass_kg'] as number | null,
    ambient_temperature_c: raw['ambient_temperature_c'] as number | null,
    notes: raw['notes'] as string | null,
    stages,
  };
}

export function validatePerformanceLabPayload(raw: unknown): PerformanceLabValidationResult {
  if (!isObject(raw)) {
    return { valid: false, reason: 'Payload is not an object.' };
  }

  if (!Array.isArray(raw['entries'])) {
    return { valid: false, reason: 'entries must be an array.' };
  }

  const entries: PerformanceHistoryEntryWire[] = [];

  for (const rawEntry of raw['entries'] as unknown[]) {
    if (!isObject(rawEntry)) {
      return { valid: false, reason: 'Entry is not an object.' };
    }

    const session = validateSession(rawEntry['session']);
    if (!session) {
      return { valid: false, reason: 'Invalid or missing session object.' };
    }

    let lactate_curve: LactateCurveWire | null = null;
    if (rawEntry['lactate_curve'] !== null && rawEntry['lactate_curve'] !== undefined) {
      lactate_curve = validateLactateCurve(rawEntry['lactate_curve'], session.test_id);
      if (!lactate_curve) {
        return { valid: false, reason: 'Invalid lactate_curve object.' };
      }
    }

    let threshold_analysis: LactateThresholdAnalysisWire | null = null;
    if (rawEntry['threshold_analysis'] !== null && rawEntry['threshold_analysis'] !== undefined) {
      threshold_analysis = validateThresholdAnalysis(rawEntry['threshold_analysis'], session.test_id);
      if (!threshold_analysis) {
        return { valid: false, reason: 'Invalid threshold_analysis object.' };
      }
    }

    entries.push({
      session,
      lactate_curve,
      threshold_analysis,
    });
  }

  return {
    valid: true,
    data: { entries },
  };
}

// ── API Client ────────────────────────────────────────────────────────────────

export interface PerformanceLabApiClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
}

export class PerformanceLabApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(options: PerformanceLabApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? '';
    this.timeoutMs = options.timeoutMs ?? 10000;
  }

  async getHistory(): Promise<PerformanceLabApiResult> {
    const url = `${this.baseUrl}/api/v1/performance-lab/history`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.status === 503) {
        return {
          success: false,
          error: {
            type: 'server_unavailable',
            message: 'Performance Lab service is temporarily unavailable.',
          },
        };
      }

      if (!response.ok) {
        return {
          success: false,
          error: {
            type: 'server_error',
            message: `Server returned HTTP status ${response.status}.`,
          },
        };
      }

      let jsonText: string;
      try {
        jsonText = await response.text();
      } catch {
        return {
          success: false,
          error: {
            type: 'network_error',
            message: 'Failed to read response body from network.',
          },
        };
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(jsonText);
      } catch {
        return {
          success: false,
          error: {
            type: 'invalid_data',
            message: 'Response payload is not valid JSON.',
          },
        };
      }

      const validation = validatePerformanceLabPayload(parsed);
      if (!validation.valid) {
        return {
          success: false,
          error: {
            type: 'invalid_data',
            message: `Invalid performance lab payload: ${validation.reason}`,
          },
        };
      }

      return {
        success: true,
        data: validation.data,
      };

    } catch (err: unknown) {
      clearTimeout(timeoutId);

      if (err instanceof Error && err.name === 'AbortError') {
        return {
          success: false,
          error: {
            type: 'timeout',
            message: 'Request timed out after waiting for response.',
          },
        };
      }

      return {
        success: false,
        error: {
          type: 'network_error',
          message: 'Network request failed or endpoint unreachable.',
        },
      };
    }
  }
}
