import { describe, expect, it, vi } from "vitest";
import { parseAndMapAthleteDashboardToBody } from "../src/mappers/body-composition-mapper";
import { renderBodyCompositionExperience } from "../src/features/body-composition/body-composition-view";
import { createBodyCompositionApp } from "../src/app/create-app";
import { resolveApplicationView } from "../src/app/view-routing";
import { resolveBodyPreviewState } from "../src/app/preview-state";
import { bodyCompositionPreviewStates } from "../src/preview-data/body-composition-preview-data";
import { payloadFixtures } from "../src/fixtures/athlete-dashboard-payload-fixtures";
import type { MappingContext } from "../src/mappers/mapping-context";
import type { AthleteDashboardPayloadV1 } from "../src/contracts/athlete-dashboard-payload-v1";

const mockContext: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 24 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("Body Composition Experience", () => {
  describe("State Rendering", () => {
    it("renders ready state with hero narrative, key changes, trend, breakdown, and technical metrics", () => {
      const state = bodyCompositionPreviewStates.ready;
      const element = renderBodyCompositionExperience(state);

      expect(element.querySelector("h1")?.textContent).toBe("Skład ciała");
      expect(element.querySelector(".body-hero__headline")?.textContent).toContain("Masa ciała zmienia się");
      expect(element.querySelectorAll(".change-card-item").length).toBe(4);
      expect(element.querySelector(".body-trend-section")).not.toBeNull();
      expect(element.querySelector(".body-breakdown-section")).not.toBeNull();
      expect(element.querySelector(".goal-alignment-section")).not.toBeNull();
      expect(element.querySelector(".data-quality-section")).not.toBeNull();
      expect(element.querySelector(".technical-metrics-section")).not.toBeNull();
    });

    it("renders partial state with notice detailing missing items", () => {
      const state = bodyCompositionPreviewStates.partial;
      const element = renderBodyCompositionExperience(state);

      const notice = element.querySelector(".state-notice--partial");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Częściowe dane");
    });

    it("renders unavailable state with unavailability notice and reason", () => {
      const state = bodyCompositionPreviewStates.unavailable;
      const element = renderBodyCompositionExperience(state);

      const notice = element.querySelector(".state-notice--unavailable");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("niedostępne");
    });

    it("renders stale state with staleness notice and last updated text", () => {
      const state = bodyCompositionPreviewStates.stale;
      const element = renderBodyCompositionExperience(state);

      const notice = element.querySelector(".state-notice--stale");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Dane wymagają odświeżenia");
    });

    it("renders loading state with skeleton layout and aria-busy='true'", () => {
      const state = bodyCompositionPreviewStates.loading;
      const element = renderBodyCompositionExperience(state);

      const main = element.querySelector("main");
      expect(main?.getAttribute("aria-busy")).toBe("true");
      expect(element.querySelector(".loading-label")?.textContent).toContain("Trwa analiza");
      expect(element.querySelectorAll(".skeleton-block").length).toBeGreaterThan(0);
    });

    it("renders failure state with retry button", () => {
      const onRetry = vi.fn();
      const state = bodyCompositionPreviewStates.failure;
      const element = renderBodyCompositionExperience(state, () => undefined, onRetry);

      const notice = element.querySelector(".state-notice--failure");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Nie udało się odświeżyć");

      const retryBtn = element.querySelector<HTMLButtonElement>(".primary-action");
      expect(retryBtn).not.toBeNull();
      retryBtn?.click();
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe("Routing & Navigation", () => {
    it("resolves view=body to body", () => {
      expect(resolveApplicationView("?view=body")).toBe("body");
      expect(resolveApplicationView("?view=body&state=partial")).toBe("body");
    });

    it("resolves preview state by query parameter", () => {
      expect(resolveBodyPreviewState("?state=partial", bodyCompositionPreviewStates).kind).toBe("partial");
      expect(resolveBodyPreviewState("?state=unavailable", bodyCompositionPreviewStates).kind).toBe("unavailable");
      expect(resolveBodyPreviewState("?state=stale", bodyCompositionPreviewStates).kind).toBe("stale");
      expect(resolveBodyPreviewState("?state=loading", bodyCompositionPreviewStates).kind).toBe("loading");
      expect(resolveBodyPreviewState("?state=failure", bodyCompositionPreviewStates).kind).toBe("failure");
      expect(resolveBodyPreviewState("", bodyCompositionPreviewStates).kind).toBe("ready");
    });

    it("triggers back navigation callback when back button is clicked", () => {
      document.body.replaceChildren();
      const onBack = vi.fn();
      document.body.append(createBodyCompositionApp(bodyCompositionPreviewStates.ready, onBack));

      const backBtn = document.querySelector<HTMLButtonElement>(".back-button");
      expect(backBtn).not.toBeNull();
      expect(backBtn?.getAttribute("aria-label")).toBe("Wróć do Dzisiaj");
      backBtn?.click();
      expect(onBack).toHaveBeenCalledOnce();
    });
  });

  describe("Payload Mode Strict Rules & Human-First UX", () => {
    it("does NOT show fake waist or fake body fat when fields are null in payload mode", () => {
      const payloadWithNulls: AthleteDashboardPayloadV1 = JSON.parse(JSON.stringify(payloadFixtures.ready));
      (payloadWithNulls.body_composition as unknown as Record<string, unknown>).waist_circumference_cm = null;
      (payloadWithNulls.body_composition as unknown as Record<string, unknown>).body_fat_percent = null;

      const result = parseAndMapAthleteDashboardToBody(payloadWithNulls, mockContext);
      expect(result.kind).toBe("partial");
      if (result.kind === "partial") {
        const labels = result.body.keyChanges.map((item) => item.label);
        expect(labels).not.toContain("Obwód talii");
        expect(labels).not.toContain("Tkanka tłuszczowa");

        const dataQualityLimit = result.body.dataQuality.limitations;
        expect(dataQualityLimit).toContain("Brak pomiaru obwodu talii");
        expect(dataQualityLimit).toContain("Brak pomiaru tkanki tłuszczowej");
      }
    });

    it("does NOT render sparkline bars or calculate BMI when height is not in payload", () => {
      const payloadNoTrend: AthleteDashboardPayloadV1 = JSON.parse(JSON.stringify(payloadFixtures.ready));
      (payloadNoTrend.body_composition as unknown as Record<string, unknown>).trend_baseline_body_mass_kg = null;

      const result = parseAndMapAthleteDashboardToBody(payloadNoTrend, mockContext);
      if (result.kind === "ready" || result.kind === "partial") {
        expect(result.body.trend.isAvailable).toBe(false);
        const techMetrics = result.body.technical.metrics;
        expect(techMetrics.find((m) => m.label.includes("BMI"))).toBeUndefined();
      }
    });

    it("maps missing body mass to unavailable state", () => {
      const payloadNoBodyMass: AthleteDashboardPayloadV1 = JSON.parse(JSON.stringify(payloadFixtures.ready));
      (payloadNoBodyMass.body_composition as unknown as Record<string, unknown>).current_body_mass_kg = null;

      const result = parseAndMapAthleteDashboardToBody(payloadNoBodyMass, mockContext);
      expect(result.kind).toBe("unavailable");
      if (result.kind === "unavailable") {
        expect(result.reason).toContain("Brak zarejestrowanych pomiarów masy ciała");
      }
    });

    it("makes data quality explicit and visible", () => {
      const element = renderBodyCompositionExperience(bodyCompositionPreviewStates.partial);
      const qualityCard = element.querySelector(".data-quality-card");
      expect(qualityCard).not.toBeNull();
      expect(qualityCard?.textContent).toContain("Ograniczenia danych");
    });
  });
});
