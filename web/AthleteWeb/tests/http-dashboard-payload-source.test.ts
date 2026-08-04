import { describe, expect, it, vi } from "vitest";
import { HttpDashboardPayloadSource } from "../src/app/dashboard-payload-source";
import { parseAndMapAthleteDashboardToMorningBriefing } from "../src/mappers/morning-briefing-mapper";
import type { MappingContext } from "../src/mappers/mapping-context";
import type { AthleteDashboardPayloadV1 } from "../src/contracts/athlete-dashboard-payload-v1";

const sampleMappingContext: MappingContext = {
  now: new Date("2026-08-03T10:00:00Z"),
  staleAfterMs: 86400000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

const validHttpPayloadV1: AthleteDashboardPayloadV1 = {
  contract_version: "1.0",
  valid_for_date: "2026-08-03",
  as_of: "2026-08-03T08:00:00Z",
  health: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    hrv_ms: 60,
    resting_heart_rate_bpm: 50,
    sleep_minutes: 490,
    steps: 11000,
    active_energy_kcal: 600,
    resting_energy_kcal: 1750,
    respiratory_rate_per_minute: 13.5,
    oxygen_saturation_percent: 99,
    wrist_temperature_celsius: 36.6,
  },
  recovery: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    recovery_score: 88,
    sleep_score: 92,
  },
  performance: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    weekly_training_load_tss: 380,
    monthly_training_load_tss: 1450,
    fatigue_tss_per_day: 40,
    fitness_tss_per_day: 65,
    form_tss_per_day: 20,
  },
  training: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    workout_name: "Tempo Ride 90 min",
    workout_goal: "TEMPO",
    estimated_duration_minutes: 90,
    target_tss: 80,
    target_if: 0.80,
    decision_action: "tempo",
    decision_reasons: ["insight_high_training_compliance"],
  },
  nutrition: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    observed_daily_expenditure_kcal: 2600,
    estimated_daily_requirement_kcal: 2700,
    carbohydrate_target_g: 350,
    protein_target_g: 150,
    carbohydrate_target_g_per_kg: 4.5,
    protein_target_g_per_kg: 2.0,
    hydration_daily_ml: 3000,
    hydration_during_workout_ml_per_hour: 800,
    fueling_pre_workout_carbohydrate_g: 70,
    fueling_during_workout_carbohydrate_g_per_hour: 50,
    fueling_post_workout_carbohydrate_g: 90,
    fueling_post_workout_protein_g: 35,
  },
  body_composition: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    current_body_mass_kg: 75.0,
    body_fat_percent: 14.0,
    muscle_mass_kg: 62.5,
    body_water_percent: 61.0,
    visceral_fat_rating: 4,
    basal_metabolic_rate_kcal: 1760,
    waist_circumference_cm: 79.5,
    trend_baseline_body_mass_kg: 76.0,
    trend_period_days: 30,
    trend_absolute_change_kg: -1.0,
    trend_percentage_change: -1.3,
  },
  goal: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    goal_type: "reduce_body_mass",
    target_body_mass_kg: 73.0,
    valid_from: "2026-07-01",
    valid_until: "2026-10-01",
  },
  recommendations: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    items: [
      {
        id: "rec-http-1",
        recommendation_type: "increase_hydration",
        priority: "medium",
        source_confidence: 0.95,
        message: "Nawadniaj się regularnie w ciągu dnia.",
        evidence: ["Wysoka temperatura"],
        source_rules: ["rule-hydration"],
        as_of: "2026-08-03T08:00:00Z",
      },
    ],
  },
  data_quality: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    body_composition_status: "complete",
    nutrition_status: "complete",
    goal_status: "complete",
    trend_quality_status: "complete",
    global_limitations: [],
  },
};

describe("HttpDashboardPayloadSource", () => {
  it("performs GET request and returns unknown data type", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => validHttpPayloadV1,
    });
    vi.stubGlobal("fetch", mockFetch);

    const source = new HttpDashboardPayloadSource("http://127.0.0.1:8000/api/v1/dashboard");
    const data = await source.load();

    expect(mockFetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/dashboard");
    expect(data).toEqual(validHttpPayloadV1);

    vi.unstubAllGlobals();
  });

  it("throws transport error on non-2xx status code", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });
    vi.stubGlobal("fetch", mockFetch);

    const source = new HttpDashboardPayloadSource("http://127.0.0.1:8000/api/v1/dashboard");
    await expect(source.load()).rejects.toThrow("HTTP 500");

    vi.unstubAllGlobals();
  });

  it("throws error on invalid JSON response body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON");
      },
    });
    vi.stubGlobal("fetch", mockFetch);

    const source = new HttpDashboardPayloadSource("http://127.0.0.1:8000/api/v1/dashboard");
    await expect(source.load()).rejects.toThrow("Unexpected token");

    vi.unstubAllGlobals();
  });

  it("throws transport error on network abort / timeout", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", mockFetch);

    const source = new HttpDashboardPayloadSource("http://127.0.0.1:8000/api/v1/dashboard");
    await expect(source.load()).rejects.toThrow("Failed to fetch");

    vi.unstubAllGlobals();
  });

  it("reuses existing runtime parser and mapper without preview data leakage", () => {
    const state = parseAndMapAthleteDashboardToMorningBriefing(validHttpPayloadV1, sampleMappingContext);
    expect(state.kind).toBe("ready");
    if (state.kind === "ready") {
      expect(state.briefing.decision.title).toBe("Tempo Ride 90 min");
    }
  });
});
