export type DashboardSectionStatus = "ready" | "partial" | "unavailable";
export type DashboardCompletenessStatus = "complete" | "partial" | "insufficient_data";
export type DashboardGoalType = "maintain" | "reduce_body_mass";
export type DashboardTrainingObjective =
  | "REST" | "RECOVERY" | "ENDURANCE" | "TEMPO" | "SWEET_SPOT"
  | "THRESHOLD" | "VO2" | "ANAEROBIC" | "SPRINT";
export type DashboardWorkoutType = "recovery" | "endurance" | "tempo" | "threshold" | "vo2";
export type DashboardDecisionReason =
  | "adaptation_reduce_load"
  | "insight_need_more_recovery"
  | "insight_fatigue_accumulating"
  | "insight_high_training_compliance";
export type DashboardRecommendationType =
  | "extend_sleep"
  | "increase_hydration"
  | "increase_carbohydrate_intake"
  | "perform_mobility"
  | "limit_additional_activity"
  | "apply_recovery_protocol"
  | "review_body_composition_trend";
export type DashboardRecommendationPriority = "high" | "medium" | "low";

export interface DashboardSectionMetadataPayloadV1 {
  readonly status: DashboardSectionStatus;
  readonly completeness_score: number | null;
  readonly limitations: readonly string[];
  readonly evidence: readonly string[];
}

export interface DashboardHealthPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly hrv_ms: number | null;
  readonly resting_heart_rate_bpm: number | null;
  readonly sleep_minutes: number | null;
  readonly steps: number | null;
  readonly active_energy_kcal: number | null;
  readonly resting_energy_kcal: number | null;
  readonly respiratory_rate_per_minute: number | null;
  readonly oxygen_saturation_percent: number | null;
  readonly wrist_temperature_celsius: number | null;
}

export interface DashboardRecoveryPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly recovery_score: number | null;
  readonly sleep_score: number | null;
}

export interface DashboardPerformancePayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly weekly_training_load_tss: number | null;
  readonly monthly_training_load_tss: number | null;
  readonly fatigue_tss_per_day: number | null;
  readonly fitness_tss_per_day: number | null;
  readonly form_tss_per_day: number | null;
}

export interface DashboardTrainingPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly workout_name: string | null;
  readonly workout_goal: DashboardTrainingObjective | null;
  readonly estimated_duration_minutes: number | null;
  readonly target_tss: number | null;
  readonly target_if: number | null;
  readonly decision_action: DashboardWorkoutType | null;
  readonly decision_reasons: readonly DashboardDecisionReason[];
}

export interface DashboardNutritionPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly observed_daily_expenditure_kcal: number | null;
  readonly estimated_daily_requirement_kcal: number | null;
  readonly carbohydrate_target_g: number | null;
  readonly protein_target_g: number | null;
  readonly carbohydrate_target_g_per_kg: number | null;
  readonly protein_target_g_per_kg: number | null;
  readonly hydration_daily_ml: number | null;
  readonly hydration_during_workout_ml_per_hour: number | null;
  readonly fueling_pre_workout_carbohydrate_g: number | null;
  readonly fueling_during_workout_carbohydrate_g_per_hour: number | null;
  readonly fueling_post_workout_carbohydrate_g: number | null;
  readonly fueling_post_workout_protein_g: number | null;
}

export interface DashboardBodyCompositionPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly current_body_mass_kg: number | null;
  readonly body_fat_percent: number | null;
  readonly muscle_mass_kg: number | null;
  readonly body_water_percent: number | null;
  readonly visceral_fat_rating: number | null;
  readonly basal_metabolic_rate_kcal: number | null;
  readonly waist_circumference_cm: number | null;
  readonly trend_baseline_body_mass_kg: number | null;
  readonly trend_period_days: number | null;
  readonly trend_absolute_change_kg: number | null;
  readonly trend_percentage_change: number | null;
}

export interface DashboardGoalPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly goal_type: DashboardGoalType | null;
  readonly target_body_mass_kg: number | null;
  readonly valid_from: string | null;
  readonly valid_until: string | null;
}

export interface DashboardRecommendationItemPayloadV1 {
  readonly id: string;
  readonly recommendation_type: DashboardRecommendationType;
  readonly priority: DashboardRecommendationPriority;
  readonly source_confidence: number;
  readonly message: string;
  readonly evidence: readonly string[];
  readonly source_rules: readonly string[];
  readonly as_of: string;
}

export interface DashboardRecommendationsPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly items: readonly DashboardRecommendationItemPayloadV1[];
}

export interface DashboardDataQualityPayloadV1 {
  readonly metadata: DashboardSectionMetadataPayloadV1;
  readonly body_composition_status: DashboardCompletenessStatus | null;
  readonly nutrition_status: DashboardCompletenessStatus | null;
  readonly goal_status: DashboardCompletenessStatus | null;
  readonly trend_quality_status: DashboardCompletenessStatus | null;
  readonly global_limitations: readonly string[];
}

export interface AthleteDashboardPayloadV1 {
  readonly contract_version: "1.0";
  readonly valid_for_date: string;
  readonly as_of: string;
  readonly health: DashboardHealthPayloadV1;
  readonly recovery: DashboardRecoveryPayloadV1;
  readonly performance: DashboardPerformancePayloadV1;
  readonly training: DashboardTrainingPayloadV1;
  readonly nutrition: DashboardNutritionPayloadV1;
  readonly body_composition: DashboardBodyCompositionPayloadV1;
  readonly goal: DashboardGoalPayloadV1;
  readonly recommendations: DashboardRecommendationsPayloadV1;
  readonly data_quality: DashboardDataQualityPayloadV1;
}
