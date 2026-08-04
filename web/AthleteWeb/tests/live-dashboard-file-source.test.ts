import { describe, expect, it, vi } from "vitest";
import { StaticJsonDashboardPayloadSource } from "../src/app/dashboard-payload-source";
import { parseAndMapAthleteDashboardToMorningBriefing } from "../src/mappers/morning-briefing-mapper";
import { parseAndMapAthleteDashboardToRecovery } from "../src/mappers/recovery-mapper";
import { parseAndMapAthleteDashboardToTraining } from "../src/mappers/training-mapper";
import { parseAndMapAthleteDashboardToProgress } from "../src/mappers/progress-mapper";
import { parseAndMapAthleteDashboardToNutrition } from "../src/mappers/nutrition-mapper";
import { parseAndMapAthleteDashboardToBody } from "../src/mappers/body-composition-mapper";
import type { MappingContext } from "../src/mappers/mapping-context";
import type { AthleteDashboardPayloadV1 } from "../src/contracts/athlete-dashboard-payload-v1";

const sampleMappingContext: MappingContext = {
  now: new Date("2026-08-03T10:00:00Z"),
  staleAfterMs: 86400000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

const validPayloadV1: AthleteDashboardPayloadV1 = {
  contract_version: "1.0",
  valid_for_date: "2026-08-03",
  as_of: "2026-08-03T08:00:00Z",
  health: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    hrv_ms: 55,
    resting_heart_rate_bpm: 52,
    sleep_minutes: 480,
    steps: 10000,
    active_energy_kcal: 500,
    resting_energy_kcal: 1800,
    respiratory_rate_per_minute: 14,
    oxygen_saturation_percent: 98,
    wrist_temperature_celsius: 36.5,
  },
  recovery: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    recovery_score: 85,
    sleep_score: 90,
  },
  performance: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    weekly_training_load_tss: 350,
    monthly_training_load_tss: 1400,
    fatigue_tss_per_day: 45,
    fitness_tss_per_day: 60,
    form_tss_per_day: 15,
  },
  training: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    workout_name: "Intervals 4x8 min",
    workout_goal: "THRESHOLD",
    estimated_duration_minutes: 60,
    target_tss: 65,
    target_if: 0.85,
    decision_action: "threshold",
    decision_reasons: ["adaptation_reduce_load"],
  },
  nutrition: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    observed_daily_expenditure_kcal: 2300,
    estimated_daily_requirement_kcal: 2500,
    carbohydrate_target_g: 300,
    protein_target_g: 140,
    carbohydrate_target_g_per_kg: 4.0,
    protein_target_g_per_kg: 1.8,
    hydration_daily_ml: 2500,
    hydration_during_workout_ml_per_hour: 750,
    fueling_pre_workout_carbohydrate_g: 60,
    fueling_during_workout_carbohydrate_g_per_hour: 45,
    fueling_post_workout_carbohydrate_g: 80,
    fueling_post_workout_protein_g: 30,
  },
  body_composition: {
    metadata: { status: "ready", completeness_score: 1, limitations: [], evidence: [] },
    current_body_mass_kg: 75.5,
    body_fat_percent: 14.2,
    muscle_mass_kg: 62.0,
    body_water_percent: 60.5,
    visceral_fat_rating: 4,
    basal_metabolic_rate_kcal: 1750,
    waist_circumference_cm: 80.0,
    trend_baseline_body_mass_kg: 76.5,
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
        id: "rec-1",
        recommendation_type: "increase_carbohydrate_intake",
        priority: "high",
        source_confidence: 0.9,
        message: "Wykonaj dzisiaj trening w strefie progu.",
        evidence: ["HRV w normie"],
        source_rules: ["rule-1"],
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

describe("Live Dashboard File Integration", () => {
  describe("StaticJsonDashboardPayloadSource", () => {
    it("returns unknown data type from load()", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => validPayloadV1,
      });
      vi.stubGlobal("fetch", mockFetch);

      const source = new StaticJsonDashboardPayloadSource("/data/test.json");
      const data = await source.load();
      expect(data).toEqual(validPayloadV1);
      vi.unstubAllGlobals();
    });

    it("throws error when fetch response is not ok", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      });
      vi.stubGlobal("fetch", mockFetch);

      const source = new StaticJsonDashboardPayloadSource("/data/missing.json");
      await expect(source.load()).rejects.toThrow("HTTP 404");
      vi.unstubAllGlobals();
    });
  });

  describe("Parser & Mapper with Live File Payload", () => {
    it("Morning Briefing maps correctly from live payload without preview data leaks", () => {
      const state = parseAndMapAthleteDashboardToMorningBriefing(validPayloadV1, sampleMappingContext);
      expect(state.kind).toBe("ready");
      if (state.kind === "ready") {
        expect(state.briefing.decision.title).toBe("Intervals 4x8 min");
      }
    });

    it("Training maps correctly from live payload", () => {
      const state = parseAndMapAthleteDashboardToTraining(validPayloadV1, sampleMappingContext);
      expect(state.kind).toBe("ready");
      if (state.kind === "ready") {
        expect(state.training.hero.title).toBe("Intervals 4x8 min");
      }
    });

    it("Recovery maps correctly from live payload", () => {
      const state = parseAndMapAthleteDashboardToRecovery(validPayloadV1, sampleMappingContext);
      expect(state.kind).toBe("ready");
      if (state.kind === "ready") {
        expect(state.recovery.hero.score).toBe(85);
      }
    });

    it("Progress does not invent missing trends if trend data is null", () => {
      const nullTrendPayload = {
        ...validPayloadV1,
        body_composition: {
          ...validPayloadV1.body_composition,
          trend_baseline_body_mass_kg: null,
          trend_period_days: null,
          trend_absolute_change_kg: null,
          trend_percentage_change: null,
        },
      };
      const state = parseAndMapAthleteDashboardToProgress(nullTrendPayload, sampleMappingContext);
      expect(state.kind).toBe("ready");
    });

    it("Nutrition does not invent missing fueling plans if nutrition values are null", () => {
      const nullNutritionPayload = {
        ...validPayloadV1,
        nutrition: {
          ...validPayloadV1.nutrition,
          fueling_pre_workout_carbohydrate_g: null,
          fueling_during_workout_carbohydrate_g_per_hour: null,
          fueling_post_workout_carbohydrate_g: null,
          fueling_post_workout_protein_g: null,
        },
      };
      const state = parseAndMapAthleteDashboardToNutrition(nullNutritionPayload, sampleMappingContext);
      expect(state.kind).toBe("ready");
    });

    it("Body Composition does not invent missing metrics if values are null", () => {
      const nullBodyPayload = {
        ...validPayloadV1,
        body_composition: {
          ...validPayloadV1.body_composition,
          metadata: { status: "unavailable" as const, completeness_score: null, limitations: [], evidence: [] },
          current_body_mass_kg: null,
          body_fat_percent: null,
        },
      };
      const state = parseAndMapAthleteDashboardToBody(nullBodyPayload, sampleMappingContext);
      expect(state.kind).toBe("unavailable");
    });
  });
});
