export type DecisionActionWire =
  | 'proceed'
  | 'reduce'
  | 'replace_with_recovery'
  | 'rest'
  | 'review';

export type DecisionSeverityWire = 'low' | 'medium' | 'high' | 'critical';

export type ContextDataStatusWire = 'available' | 'partial' | 'unavailable' | 'stale';

export type RecommendationCategoryWire =
  | 'training'
  | 'recovery'
  | 'laboratory'
  | 'data_quality'
  | 'performance';

export type RecommendationPriorityWire = 'low' | 'medium' | 'high' | 'critical';

export interface RecoveryDecisionContextWire {
  status: ContextDataStatusWire;
  recovery_score: number | null;
  recovery_status: string | null;
  hrv_status: string | null;
  resting_heart_rate_status: string | null;
  sleep_status: string | null;
  generated_at: string | null;
}

export interface TrainingDecisionContextWire {
  status: ContextDataStatusWire;
  planned_session_type: string | null;
  planned_duration_minutes: number | null;
  planned_intensity: string | null;
  recent_training_load: number | null;
  fatigue_status: string | null;
  generated_at: string | null;
}

export interface BiomarkerDecisionSignalWire {
  canonical_code: string;
  interpretation: string;
  confidence: string;
  summary: string | null;
}

export interface BiomarkerDecisionContextWire {
  status: ContextDataStatusWire;
  attention_count: number;
  critical_count: number;
  signals: readonly BiomarkerDecisionSignalWire[];
  generated_at: string | null;
}

export interface PerformanceThresholdSnapshotWire {
  name: string;
  status: string;
  power_watts: number | null;
  speed_kph: number | null;
  heart_rate_bpm: number | null;
  lactate_mmol_l: number | null;
  confidence: number | null;
  method: string | null;
}

export interface PerformanceDecisionContextWire {
  status: ContextDataStatusWire;
  latest_test_id: string | null;
  latest_test_type: string | null;
  performed_at: string | null;
  lt1: PerformanceThresholdSnapshotWire | null;
  lt2: PerformanceThresholdSnapshotWire | null;
}

export interface AthleteDecisionContextWire {
  generated_at: string;
  recovery: RecoveryDecisionContextWire;
  training: TrainingDecisionContextWire;
  biomarkers: BiomarkerDecisionContextWire;
  performance: PerformanceDecisionContextWire;
}

export interface DecisionPolicySignalWire {
  code: string;
  source: string;
  severity: DecisionSeverityWire;
  summary: string;
}

export interface DecisionPolicyResultWire {
  generated_at: string;
  action: DecisionActionWire;
  severity: DecisionSeverityWire;
  signals: readonly DecisionPolicySignalWire[];
  confidence: number;
  policy_version: string;
}

export interface DecisionRecommendationWire {
  code: string;
  category: RecommendationCategoryWire;
  priority: RecommendationPriorityWire;
  title: string;
  description: string;
  source_signal_codes: readonly string[];
}

export interface DecisionExplanationItemWire {
  signal_code: string;
  source: string;
  severity: DecisionSeverityWire;
  summary: string;
}

export interface DecisionExplanationWire {
  headline: string;
  summary: string;
  items: readonly DecisionExplanationItemWire[];
}

export interface RecommendationPlanWire {
  generated_at: string;
  action: DecisionActionWire;
  severity: DecisionSeverityWire;
  confidence: number;
  policy_version: string;
  recommendations: readonly DecisionRecommendationWire[];
  explanation: DecisionExplanationWire;
}

export interface DecisionAuditRecordWire {
  decision_id: string;
  recorded_at: string;
  context: AthleteDecisionContextWire;
  policy_result: DecisionPolicyResultWire;
  recommendation_plan: RecommendationPlanWire;
}

export interface DecisionIntelligenceApiResponseWire {
  decision: DecisionAuditRecordWire | null;
}

export interface DecisionValidationResult<T> {
  valid: boolean;
  data?: T;
  error?: string;
}
