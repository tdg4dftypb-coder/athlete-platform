import type { AthleteDashboardPayloadV1 } from "./athlete-dashboard-payload-v1";

export interface PayloadValidationIssue {
  readonly path: string;
  readonly message: string;
}

export type AthleteDashboardPayloadParseResult =
  | { readonly success: true; readonly data: AthleteDashboardPayloadV1 }
  | { readonly success: false; readonly issues: readonly PayloadValidationIssue[] };

const rootKeys = [
  "contract_version", "valid_for_date", "as_of", "health", "recovery", "performance",
  "training", "nutrition", "body_composition", "goal", "recommendations", "data_quality",
] as const;
const metadataKeys = ["status", "completeness_score", "limitations", "evidence"] as const;
const sectionStatuses = ["ready", "partial", "unavailable"] as const;
const completenessStatuses = ["complete", "partial", "insufficient_data"] as const;
const goalTypes = ["maintain", "reduce_body_mass"] as const;
const trainingObjectives = [
  "REST", "RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD", "VO2", "ANAEROBIC", "SPRINT",
] as const;
const workoutTypes = ["recovery", "endurance", "tempo", "threshold", "vo2"] as const;
const decisionReasons = [
  "adaptation_reduce_load", "insight_need_more_recovery", "insight_fatigue_accumulating",
  "insight_high_training_compliance",
] as const;
const recommendationTypes = [
  "extend_sleep", "increase_hydration", "increase_carbohydrate_intake", "perform_mobility",
  "limit_additional_activity", "apply_recovery_protocol", "review_body_composition_trend",
] as const;
const recommendationPriorities = ["high", "medium", "low"] as const;

const sectionSpecs = {
  health: {
    numbers: ["hrv_ms", "resting_heart_rate_bpm", "active_energy_kcal", "resting_energy_kcal", "respiratory_rate_per_minute", "oxygen_saturation_percent", "wrist_temperature_celsius"],
    integers: ["sleep_minutes", "steps"],
  },
  recovery: { numbers: [], integers: ["recovery_score", "sleep_score"] },
  performance: {
    numbers: ["weekly_training_load_tss", "monthly_training_load_tss", "fatigue_tss_per_day", "fitness_tss_per_day", "form_tss_per_day"],
    integers: [],
  },
  nutrition: {
    numbers: [
      "observed_daily_expenditure_kcal", "estimated_daily_requirement_kcal", "carbohydrate_target_g",
      "protein_target_g", "carbohydrate_target_g_per_kg", "protein_target_g_per_kg", "hydration_daily_ml",
      "hydration_during_workout_ml_per_hour", "fueling_pre_workout_carbohydrate_g",
      "fueling_during_workout_carbohydrate_g_per_hour", "fueling_post_workout_carbohydrate_g",
      "fueling_post_workout_protein_g",
    ],
    integers: [],
  },
  body_composition: {
    numbers: [
      "current_body_mass_kg", "body_fat_percent", "muscle_mass_kg", "body_water_percent",
      "visceral_fat_rating", "basal_metabolic_rate_kcal", "waist_circumference_cm",
      "trend_baseline_body_mass_kg", "trend_absolute_change_kg", "trend_percentage_change",
    ],
    integers: ["trend_period_days"],
  },
} as const;

export function parseAthleteDashboardPayloadV1(input: unknown): AthleteDashboardPayloadParseResult {
  const issues: PayloadValidationIssue[] = [];
  const root = objectWithExactKeys(input, "dashboard", rootKeys, issues);
  if (!root) return { success: false, issues };

  if (root.contract_version !== "1.0") issue(issues, "dashboard.contract_version", "must equal '1.0'");
  validateDate(root.valid_for_date, "dashboard.valid_for_date", issues, false);
  validateDateTime(root.as_of, "dashboard.as_of", issues);

  for (const [sectionName, spec] of Object.entries(sectionSpecs)) {
    validateNumericSection(root[sectionName], `dashboard.${sectionName}`, spec.numbers, spec.integers, issues);
  }
  validateTraining(root.training, issues);
  validateGoal(root.goal, issues);
  validateRecommendations(root.recommendations, issues);
  validateDataQuality(root.data_quality, issues);

  return issues.length
    ? { success: false, issues }
    : { success: true, data: input as AthleteDashboardPayloadV1 };
}

function validateNumericSection(
  input: unknown,
  path: string,
  numberKeys: readonly string[],
  integerKeys: readonly string[],
  issues: PayloadValidationIssue[],
): void {
  const keys = ["metadata", ...numberKeys, ...integerKeys];
  const section = objectWithExactKeys(input, path, keys, issues);
  if (!section) return;
  validateMetadata(section.metadata, `${path}.metadata`, issues);
  for (const key of numberKeys) validateOptionalNumber(section[key], `${path}.${key}`, issues, false);
  for (const key of integerKeys) validateOptionalNumber(section[key], `${path}.${key}`, issues, true);
}

function validateTraining(input: unknown, issues: PayloadValidationIssue[]): void {
  const path = "dashboard.training";
  const keys = ["metadata", "workout_name", "workout_goal", "estimated_duration_minutes", "target_tss", "target_if", "decision_action", "decision_reasons"];
  const section = objectWithExactKeys(input, path, keys, issues);
  if (!section) return;
  validateMetadata(section.metadata, `${path}.metadata`, issues);
  validateOptionalString(section.workout_name, `${path}.workout_name`, issues);
  validateOptionalEnum(section.workout_goal, trainingObjectives, `${path}.workout_goal`, issues);
  validateOptionalNumber(section.estimated_duration_minutes, `${path}.estimated_duration_minutes`, issues, true);
  validateOptionalNumber(section.target_tss, `${path}.target_tss`, issues, false);
  validateOptionalNumber(section.target_if, `${path}.target_if`, issues, false);
  validateOptionalEnum(section.decision_action, workoutTypes, `${path}.decision_action`, issues);
  validateEnumArray(section.decision_reasons, decisionReasons, `${path}.decision_reasons`, issues);
}

function validateGoal(input: unknown, issues: PayloadValidationIssue[]): void {
  const path = "dashboard.goal";
  const section = objectWithExactKeys(input, path, ["metadata", "goal_type", "target_body_mass_kg", "valid_from", "valid_until"], issues);
  if (!section) return;
  validateMetadata(section.metadata, `${path}.metadata`, issues);
  validateOptionalEnum(section.goal_type, goalTypes, `${path}.goal_type`, issues);
  validateOptionalNumber(section.target_body_mass_kg, `${path}.target_body_mass_kg`, issues, false);
  validateDate(section.valid_from, `${path}.valid_from`, issues, true);
  validateDate(section.valid_until, `${path}.valid_until`, issues, true);
}

function validateRecommendations(input: unknown, issues: PayloadValidationIssue[]): void {
  const path = "dashboard.recommendations";
  const section = objectWithExactKeys(input, path, ["metadata", "items"], issues);
  if (!section) return;
  validateMetadata(section.metadata, `${path}.metadata`, issues);
  if (!Array.isArray(section.items)) {
    issue(issues, `${path}.items`, "must be an array");
    return;
  }
  section.items.forEach((inputItem, index) => {
    const itemPath = `${path}.items[${index}]`;
    const item = objectWithExactKeys(inputItem, itemPath, ["id", "recommendation_type", "priority", "source_confidence", "message", "evidence", "source_rules", "as_of"], issues);
    if (!item) return;
    validateString(item.id, `${itemPath}.id`, issues);
    validateEnum(item.recommendation_type, recommendationTypes, `${itemPath}.recommendation_type`, issues);
    validateEnum(item.priority, recommendationPriorities, `${itemPath}.priority`, issues);
    validateNumber(item.source_confidence, `${itemPath}.source_confidence`, issues, false);
    validateString(item.message, `${itemPath}.message`, issues);
    validateStringArray(item.evidence, `${itemPath}.evidence`, issues);
    validateStringArray(item.source_rules, `${itemPath}.source_rules`, issues);
    validateDateTime(item.as_of, `${itemPath}.as_of`, issues);
  });
}

function validateDataQuality(input: unknown, issues: PayloadValidationIssue[]): void {
  const path = "dashboard.data_quality";
  const section = objectWithExactKeys(input, path, ["metadata", "body_composition_status", "nutrition_status", "goal_status", "trend_quality_status", "global_limitations"], issues);
  if (!section) return;
  validateMetadata(section.metadata, `${path}.metadata`, issues);
  for (const key of ["body_composition_status", "nutrition_status", "goal_status", "trend_quality_status"] as const) {
    validateOptionalEnum(section[key], completenessStatuses, `${path}.${key}`, issues);
  }
  validateStringArray(section.global_limitations, `${path}.global_limitations`, issues);
}

function validateMetadata(input: unknown, path: string, issues: PayloadValidationIssue[]): void {
  const metadata = objectWithExactKeys(input, path, metadataKeys, issues);
  if (!metadata) return;
  validateEnum(metadata.status, sectionStatuses, `${path}.status`, issues);
  validateOptionalNumber(metadata.completeness_score, `${path}.completeness_score`, issues, false);
  validateStringArray(metadata.limitations, `${path}.limitations`, issues);
  validateStringArray(metadata.evidence, `${path}.evidence`, issues);
}

function objectWithExactKeys(input: unknown, path: string, expected: readonly string[], issues: PayloadValidationIssue[]): Record<string, unknown> | undefined {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    issue(issues, path, "must be an object");
    return undefined;
  }
  const value = input as Record<string, unknown>;
  const actual = Object.keys(value);
  for (const key of expected) if (!(key in value)) issue(issues, `${path}.${key}`, "is required");
  for (const key of actual) if (!expected.includes(key)) issue(issues, `${path}.${key}`, "is not allowed");
  return value;
}

function validateDate(input: unknown, path: string, issues: PayloadValidationIssue[], nullable: boolean): void {
  if (input === null && nullable) return;
  if (typeof input !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(input)) {
    issue(issues, path, nullable ? "must be a canonical ISO date or null" : "must be a canonical ISO date");
    return;
  }
  const [year, month, day] = input.split("-").map(Number);
  const date = new Date(Date.UTC(year!, month! - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month! - 1 || date.getUTCDate() !== day) {
    issue(issues, path, "must be a valid calendar date");
  }
}

function validateDateTime(input: unknown, path: string, issues: PayloadValidationIssue[]): void {
  if (typeof input !== "string") {
    issue(issues, path, "must be a canonical ISO datetime");
    return;
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))?$/.exec(input);
  if (!match || !Number.isFinite(Date.parse(input))) {
    issue(issues, path, "must be a canonical ISO datetime");
    return;
  }
  const [year, month, day, hour, minute, second] = match.slice(1, 7).map(Number);
  const calendar = new Date(Date.UTC(year!, month! - 1, day, hour, minute, second));
  const offsetHour = match[8] === undefined ? 0 : Number(match[8]);
  const offsetMinute = match[9] === undefined ? 0 : Number(match[9]);
  if (
    calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month! - 1 || calendar.getUTCDate() !== day
    || hour! > 23 || minute! > 59 || second! > 59 || offsetHour > 23 || offsetMinute > 59
  ) issue(issues, path, "must be a valid calendar datetime");
}

function validateOptionalNumber(input: unknown, path: string, issues: PayloadValidationIssue[], integer: boolean): void {
  if (input === null) return;
  validateNumber(input, path, issues, integer);
}

function validateNumber(input: unknown, path: string, issues: PayloadValidationIssue[], integer: boolean): void {
  if (typeof input !== "number" || !Number.isFinite(input) || (integer && !Number.isInteger(input))) {
    issue(issues, path, integer ? "must be a finite integer" : "must be a finite number");
  }
}

function validateOptionalString(input: unknown, path: string, issues: PayloadValidationIssue[]): void {
  if (input === null) return;
  validateString(input, path, issues);
}

function validateString(input: unknown, path: string, issues: PayloadValidationIssue[]): void {
  if (typeof input !== "string") issue(issues, path, "must be a string");
}

function validateOptionalEnum(input: unknown, allowed: readonly string[], path: string, issues: PayloadValidationIssue[]): void {
  if (input === null) return;
  validateEnum(input, allowed, path, issues);
}

function validateEnum(input: unknown, allowed: readonly string[], path: string, issues: PayloadValidationIssue[]): void {
  if (typeof input !== "string" || !allowed.includes(input)) issue(issues, path, "has an unknown enum value");
}

function validateStringArray(input: unknown, path: string, issues: PayloadValidationIssue[]): void {
  if (!Array.isArray(input)) {
    issue(issues, path, "must be an array");
    return;
  }
  input.forEach((value, index) => validateString(value, `${path}[${index}]`, issues));
}

function validateEnumArray(input: unknown, allowed: readonly string[], path: string, issues: PayloadValidationIssue[]): void {
  if (!Array.isArray(input)) {
    issue(issues, path, "must be an array");
    return;
  }
  input.forEach((value, index) => validateEnum(value, allowed, `${path}[${index}]`, issues));
}

function issue(issues: PayloadValidationIssue[], path: string, message: string): void {
  issues.push({ path, message });
}
