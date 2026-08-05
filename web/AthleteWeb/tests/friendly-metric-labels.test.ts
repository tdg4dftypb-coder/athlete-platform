import { describe, expect, it } from "vitest";
import { mapAthleteDashboardToProgress } from "../src/mappers/progress-mapper";
import { mapAthleteDashboardToRecovery } from "../src/mappers/recovery-mapper";
import { parseAndMapAthleteDashboardToTraining } from "../src/mappers/training-mapper";
import { mapAthleteDashboardToNutrition } from "../src/mappers/nutrition-mapper";
import { mapAthleteDashboardToBody } from "../src/mappers/body-composition-mapper";
import { translateRecommendationMessage } from "../src/mappers/morning-briefing-mapper";
import { payloadFixtures } from "../src/fixtures/athlete-dashboard-payload-fixtures";
import type { MappingContext } from "../src/mappers/mapping-context";

const mockContext: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 24 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("Sprint 1C — Friendly Metric Labels Presentation Contract", () => {
  it("uses 'Długoterminowa kondycja' as primary title for CTL without standalone CTL heading", () => {
    const state = mapAthleteDashboardToProgress(payloadFixtures.ready, mockContext);
    if (state.kind === "ready" || state.kind === "partial") {
      expect(state.progress.trend.title).toBe("Długoterminowa kondycja");
      expect(state.progress.trend.title).not.toBe("CTL");
    }
  });

  it("uses full friendly labels with secondary acronyms for CTL, ATL, TSB, and TSS in Progress", () => {
    const state = mapAthleteDashboardToProgress(payloadFixtures.ready, mockContext);
    if (state.kind === "ready") {
      const labels = state.progress.technicalMetrics.metrics.map((m) => m.label);
      expect(labels).toContain("Długoterminowa kondycja (CTL)");
      expect(labels).toContain("Krótkoterminowe obciążenie (ATL)");
      expect(labels).toContain("Świeżość treningowa (TSB)");
      expect(labels).toContain("Tygodniowe obciążenie (TSS)");
    }
  });

  it("uses full Polish name for HRV and RHR in Recovery factor presentation", () => {
    const state = mapAthleteDashboardToRecovery(payloadFixtures.ready, mockContext);
    if (state.kind === "ready") {
      const hrvFactor = state.recovery.factors.find((f) => f.id === "hrv");
      expect(hrvFactor?.label).toBe("Zmienność rytmu serca (HRV)");
      const rhrFactor = state.recovery.factors.find((f) => f.id === "resting-heart-rate");
      expect(rhrFactor?.label).toBe("Tętno spoczynkowe");
    }
  });

  it("keeps IF and NP strictly in technical details in Training", () => {
    const state = parseAndMapAthleteDashboardToTraining(payloadFixtures.ready, mockContext);
    if (state.kind === "ready") {
      expect(state.training.hero.title).not.toContain("IF");
      expect(state.training.hero.title).not.toContain("NP");
    }
  });

  it("describes BIA as 'Analiza impedancji (BIA)' in Body Composition", () => {
    const state = mapAthleteDashboardToBody(payloadFixtures.ready, mockContext);
    if (state.kind === "ready" || state.kind === "partial") {
      const breakdownTags = state.body.breakdown.map((b) => b.statusTag);
      expect(breakdownTags).toContain("Analiza impedancji (BIA)");
    }
  });

  it("labels observed energy expenditure clearly without calling it a calorie goal", () => {
    const state = mapAthleteDashboardToNutrition(payloadFixtures.ready, mockContext);
    if (state.kind === "ready" || state.kind === "partial") {
      const metrics = state.nutrition.technical.metrics;
      const expenditureMetric = metrics.find((m) => m.label.includes("wydatek energii"));
      expect(expenditureMetric).not.toBeUndefined();
      expect(expenditureMetric?.label).toBe("Zaobserwowany wydatek energii");
      expect(expenditureMetric?.valueText).toMatch(/\d+ kcal/);
    }
  });

  it("uses neutral Polish fallback 'Sprawdź szczegóły rekomendacji.' for unknown recommendations", () => {
    expect(translateRecommendationMessage("Unknown backend action")).toBe("Sprawdź szczegóły rekomendacji.");
  });

  it("preserves exact numeric values and units", () => {
    const nutritionState = mapAthleteDashboardToNutrition(payloadFixtures.ready, mockContext);
    if (nutritionState.kind === "ready" || nutritionState.kind === "partial") {
      const exp = nutritionState.nutrition.technical.metrics.find((m) => m.label.includes("wydatek"));
      expect(exp?.valueText).toMatch(/\d+ kcal/);
    }

    const recoveryState = mapAthleteDashboardToRecovery(payloadFixtures.ready, mockContext);
    if (recoveryState.kind === "ready") {
      const hrv = recoveryState.recovery.factors.find((f) => f.id === "hrv");
      expect(hrv?.valueText).toBe("42,5 ms");
    }
  });
});
