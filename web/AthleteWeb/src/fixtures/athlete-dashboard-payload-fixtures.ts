import type {
  AthleteDashboardPayloadV1,
  DashboardSectionMetadataPayloadV1,
} from "../contracts/athlete-dashboard-payload-v1";

const readyMetadata = {
  status: "ready",
  completeness_score: 1,
  limitations: [],
  evidence: ["preview:fixture"],
} as const;

export const readyPayloadFixture: AthleteDashboardPayloadV1 = {
  contract_version: "1.0",
  valid_for_date: "2026-08-03",
  as_of: "2026-08-03T07:30:00+02:00",
  health: {
    metadata: readyMetadata,
    hrv_ms: 42.5,
    resting_heart_rate_bpm: 51,
    sleep_minutes: 465,
    steps: 8200,
    active_energy_kcal: 620,
    resting_energy_kcal: 1780,
    respiratory_rate_per_minute: 14.2,
    oxygen_saturation_percent: 98,
    wrist_temperature_celsius: 36.1,
  },
  recovery: { metadata: readyMetadata, recovery_score: 84, sleep_score: 91 },
  performance: {
    metadata: readyMetadata,
    weekly_training_load_tss: 310,
    monthly_training_load_tss: 1210,
    fatigue_tss_per_day: 44.3,
    fitness_tss_per_day: 28.8,
    form_tss_per_day: -15.5,
  },
  training: {
    metadata: readyMetadata,
    workout_name: "Trening progowy",
    workout_goal: "THRESHOLD",
    estimated_duration_minutes: 75,
    target_tss: 62,
    target_if: null,
    decision_action: "threshold",
    decision_reasons: ["insight_high_training_compliance"],
  },
  nutrition: {
    metadata: readyMetadata,
    observed_daily_expenditure_kcal: 2400,
    estimated_daily_requirement_kcal: null,
    carbohydrate_target_g: 360,
    protein_target_g: 128,
    carbohydrate_target_g_per_kg: 4.5,
    protein_target_g_per_kg: 1.6,
    hydration_daily_ml: 2800,
    hydration_during_workout_ml_per_hour: 600,
    fueling_pre_workout_carbohydrate_g: 80,
    fueling_during_workout_carbohydrate_g_per_hour: 30,
    fueling_post_workout_carbohydrate_g: 80,
    fueling_post_workout_protein_g: 24,
  },
  body_composition: {
    metadata: readyMetadata,
    current_body_mass_kg: 80,
    body_fat_percent: 17,
    muscle_mass_kg: 61,
    body_water_percent: 55,
    visceral_fat_rating: null,
    basal_metabolic_rate_kcal: 1750,
    waist_circumference_cm: 82,
    trend_baseline_body_mass_kg: 81.5,
    trend_period_days: 28,
    trend_absolute_change_kg: -1.5,
    trend_percentage_change: -1.84,
  },
  goal: {
    metadata: readyMetadata,
    goal_type: "reduce_body_mass",
    target_body_mass_kg: 77,
    valid_from: "2026-07-01",
    valid_until: "2026-10-01",
  },
  recommendations: {
    metadata: readyMetadata,
    items: [
      {
        id: "training-quality",
        recommendation_type: "limit_additional_activity",
        priority: "high",
        source_confidence: 0.85,
        message: "Największą korzyść przyniesie jakość, nie objętość.",
        evidence: ["training:decision"],
        source_rules: ["PreviewFixtureRule"],
        as_of: "2026-08-03T07:30:00+02:00",
      },
    ],
  },
  data_quality: {
    metadata: readyMetadata,
    body_composition_status: "complete",
    nutrition_status: "complete",
    goal_status: "complete",
    trend_quality_status: "complete",
    global_limitations: [],
  },
};

export const partialPayloadFixture: AthleteDashboardPayloadV1 = copyPayload(readyPayloadFixture, (payload) => {
  payload.health.metadata = unavailableMetadata("Brak aktualnych danych HRV");
  payload.health.hrv_ms = null;
  payload.health.sleep_minutes = null;
  payload.recovery.metadata = partialMetadata("Ocena regeneracji jest niepełna");
  payload.recovery.sleep_score = null;
  payload.data_quality.metadata = partialMetadata("Część źródeł jest niedostępna");
});

export const unavailablePayloadFixture: AthleteDashboardPayloadV1 = copyPayload(readyPayloadFixture, (payload) => {
  payload.training.metadata = unavailableMetadata("Brak rekomendacji treningowej");
  payload.training.workout_name = null;
  payload.training.workout_goal = null;
  payload.training.estimated_duration_minutes = null;
  payload.training.target_tss = null;
  payload.training.decision_action = null;
  payload.training.decision_reasons = [];
  payload.recommendations.metadata = unavailableMetadata("Brak rekomendacji");
  payload.recommendations.items = [];
});

export const recoveryUnavailablePayloadFixture: AthleteDashboardPayloadV1 = copyPayload(
  readyPayloadFixture,
  (payload) => {
    payload.recovery.metadata = unavailableMetadata("Brak oceny regeneracji");
    payload.recovery.recovery_score = null;
    payload.recovery.sleep_score = null;
    payload.health.metadata = unavailableMetadata("Brak danych zdrowotnych");
    payload.health.hrv_ms = null;
    payload.health.resting_heart_rate_bpm = null;
    payload.health.sleep_minutes = null;
  },
);

export const stalePayloadFixture: AthleteDashboardPayloadV1 = copyPayload(readyPayloadFixture, (payload) => {
  payload.valid_for_date = "2026-08-02";
  payload.as_of = "2026-08-02T21:45:00+02:00";
  payload.recommendations.items[0]!.as_of = "2026-08-02T21:45:00+02:00";
});

export const invalidVersionPayloadFixture: unknown = invalidPayload((payload) => {
  payload.contract_version = "2.0";
});
export const missingSectionPayloadFixture: unknown = invalidPayload((payload) => {
  delete payload.health;
});
export const invalidEnumPayloadFixture: unknown = invalidPayload((payload) => {
  asRecord(payload.training).workout_goal = "FUTURE";
});
export const invalidDatePayloadFixture: unknown = invalidPayload((payload) => {
  payload.valid_for_date = "03-08-2026";
});
export const invalidTimestampPayloadFixture: unknown = invalidPayload((payload) => {
  payload.as_of = "tomorrow";
});
export const malformedPayloadFixture: unknown = { contract_version: "1.0", health: [] };

export const payloadFixtures = {
  ready: readyPayloadFixture,
  partial: partialPayloadFixture,
  unavailable: unavailablePayloadFixture,
  "recovery-unavailable": recoveryUnavailablePayloadFixture,
  stale: stalePayloadFixture,
  "invalid-version": invalidVersionPayloadFixture,
  "missing-section": missingSectionPayloadFixture,
  "invalid-enum": invalidEnumPayloadFixture,
  "invalid-date": invalidDatePayloadFixture,
  "invalid-timestamp": invalidTimestampPayloadFixture,
  malformed: malformedPayloadFixture,
} as const;

export type PayloadFixtureName = keyof typeof payloadFixtures;

function partialMetadata(limitation: string): DeepMutable<DashboardSectionMetadataPayloadV1> {
  return { status: "partial", completeness_score: 0.5, limitations: [limitation], evidence: [] };
}

function unavailableMetadata(limitation: string): DeepMutable<DashboardSectionMetadataPayloadV1> {
  return { status: "unavailable", completeness_score: null, limitations: [limitation], evidence: [] };
}

function copyPayload(
  source: AthleteDashboardPayloadV1,
  mutate: (payload: DeepMutable<AthleteDashboardPayloadV1>) => void,
): AthleteDashboardPayloadV1 {
  const payload = JSON.parse(JSON.stringify(source)) as DeepMutable<AthleteDashboardPayloadV1>;
  mutate(payload);
  return payload;
}

function invalidPayload(mutate: (payload: Record<string, unknown>) => void): unknown {
  const payload = JSON.parse(JSON.stringify(readyPayloadFixture)) as Record<string, unknown>;
  mutate(payload);
  return payload;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value as Record<string, unknown>;
}

type DeepMutable<T> = T extends readonly (infer Item)[]
  ? DeepMutable<Item>[]
  : T extends object
    ? { -readonly [Key in keyof T]: DeepMutable<T[Key]> }
    : T;
