/**
 * Performance Lab API Types & Validation Contracts
 */

export type PerformanceTestTypeWire =
  | 'lactate_step_test'
  | 'cardiopulmonary_exercise_test'
  | 'ftp_test'
  | 'field_test';

export type PerformanceTestStatusWire =
  | 'planned'
  | 'completed'
  | 'partial'
  | 'invalid';

export type ExerciseModalityWire =
  | 'cycling'
  | 'running'
  | 'rowing'
  | 'other';

export type StageCompletionStatusWire =
  | 'completed'
  | 'incomplete'
  | 'skipped';

export type ThresholdDetectionStatusWire =
  | 'detected'
  | 'insufficient_data'
  | 'not_reached'
  | 'invalid_curve';

export interface PerformanceStageWire {
  stage_number: number;
  duration_seconds: number | null;
  power_watts: number | null;
  speed_kph: number | null;
  heart_rate_bpm: number | null;
  lactate_mmol_l: number | null;
  cadence_rpm: number | null;
  perceived_exertion: number | null;
  completion_status: StageCompletionStatusWire;
  notes: string | null;
}

export interface PerformanceTestSessionWire {
  test_id: string;
  performed_at: string;
  test_type: PerformanceTestTypeWire;
  status: PerformanceTestStatusWire;
  modality: ExerciseModalityWire;
  protocol_name: string | null;
  body_mass_kg: number | null;
  ambient_temperature_c: number | null;
  notes: string | null;
  stages: PerformanceStageWire[];
}

export interface LactateCurvePointWire {
  stage_number: number;
  power_watts: number | null;
  speed_kph: number | null;
  heart_rate_bpm: number | null;
  lactate_mmol_l: number;
  absolute_change_mmol_l: number | null;
  relative_change_percent: number | null;
}

export interface LactateCurveWire {
  test_id: string;
  points: LactateCurvePointWire[];
}

export interface DetectedThresholdWire {
  name: string;
  status: ThresholdDetectionStatusWire;
  stage_number: number | null;
  power_watts: number | null;
  speed_kph: number | null;
  heart_rate_bpm: number | null;
  lactate_mmol_l: number | null;
  target_lactate_mmol_l: number;
  confidence: number | null;
  method: string;
}

export interface LactateThresholdAnalysisWire {
  test_id: string;
  lt1: DetectedThresholdWire;
  lt2: DetectedThresholdWire;
}

export interface PerformanceHistoryEntryWire {
  session: PerformanceTestSessionWire;
  lactate_curve: LactateCurveWire | null;
  threshold_analysis: LactateThresholdAnalysisWire | null;
}

export interface PerformanceTestHistoryWire {
  entries: PerformanceHistoryEntryWire[];
}

export type PerformanceLabValidationResult =
  | { valid: true; data: PerformanceTestHistoryWire }
  | { valid: false; reason: string };
