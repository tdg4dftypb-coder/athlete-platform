import { describe, expect, it, vi } from "vitest";
import {
  parseAndMapAthleteDashboardToNutrition,
  mapAthleteDashboardToNutrition,
} from "../src/mappers/nutrition-mapper";
import { renderNutritionExperience } from "../src/features/nutrition/nutrition-view";
import { createNutritionApp } from "../src/app/create-app";
import { resolveApplicationView } from "../src/app/view-routing";
import { resolveNutritionPreviewState } from "../src/app/preview-state";
import { nutritionPreviewStates } from "../src/preview-data/nutrition-preview-data";
import { payloadFixtures } from "../src/fixtures/athlete-dashboard-payload-fixtures";
import type { MappingContext } from "../src/mappers/mapping-context";

const mockContext: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 24 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("Nutrition Experience", () => {
  describe("State Rendering", () => {
    it("renders ready state with hero, focus items, meal timeline, hydration, coach summary, and technical metrics", () => {
      const state = nutritionPreviewStates.ready;
      const element = renderNutritionExperience(state);

      expect(element.querySelector("h1")?.textContent).toBe("Odżywianie");
      expect(element.querySelector(".nutrition-hero__headline")?.textContent).toContain("wspiera dzisiejszy trening");
      expect(element.querySelectorAll(".focus-card-item").length).toBe(4);
      expect(element.querySelectorAll(".timeline-item").length).toBe(5);
      expect(element.querySelector(".hydration-section")).not.toBeNull();
      expect(element.querySelector(".ai-summary-section")).not.toBeNull();
      expect(element.querySelector(".technical-metrics-section")).not.toBeNull();
    });

    it("renders partial state with status notice detailing missing items", () => {
      const state = nutritionPreviewStates.partial;
      const element = renderNutritionExperience(state);

      const notice = element.querySelector(".state-notice--partial");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Częściowe dane");
    });

    it("renders unavailable state with unavailability notice and reason", () => {
      const state = nutritionPreviewStates.unavailable;
      const element = renderNutritionExperience(state);

      const notice = element.querySelector(".state-notice--unavailable");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("niedostępny");
    });

    it("renders stale state with staleness notice and last updated text", () => {
      const state = nutritionPreviewStates.stale;
      const element = renderNutritionExperience(state);

      const notice = element.querySelector(".state-notice--stale");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Dane wymagają odświeżenia");
    });

    it("renders loading state with skeleton layout and aria-busy='true'", () => {
      const state = nutritionPreviewStates.loading;
      const element = renderNutritionExperience(state);

      const main = element.querySelector("main");
      expect(main?.getAttribute("aria-busy")).toBe("true");
      expect(element.querySelector(".loading-label")?.textContent).toContain("Trwa dopasowywanie");
      expect(element.querySelectorAll(".skeleton-block").length).toBeGreaterThan(0);
    });

    it("renders failure state with retry button", () => {
      const onRetry = vi.fn();
      const state = nutritionPreviewStates.failure;
      const element = renderNutritionExperience(state, () => undefined, onRetry);

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
    it("resolves view=nutrition to nutrition", () => {
      expect(resolveApplicationView("?view=nutrition")).toBe("nutrition");
      expect(resolveApplicationView("?view=nutrition&state=partial")).toBe("nutrition");
    });

    it("resolves preview state by query parameter", () => {
      expect(resolveNutritionPreviewState("?state=partial", nutritionPreviewStates).kind).toBe("partial");
      expect(resolveNutritionPreviewState("?state=unavailable", nutritionPreviewStates).kind).toBe("unavailable");
      expect(resolveNutritionPreviewState("?state=stale", nutritionPreviewStates).kind).toBe("stale");
      expect(resolveNutritionPreviewState("?state=loading", nutritionPreviewStates).kind).toBe("loading");
      expect(resolveNutritionPreviewState("?state=failure", nutritionPreviewStates).kind).toBe("failure");
      expect(resolveNutritionPreviewState("", nutritionPreviewStates).kind).toBe("ready");
    });

    it("triggers back navigation callback when back button is clicked", () => {
      document.body.replaceChildren();
      const onBack = vi.fn();
      document.body.append(createNutritionApp(nutritionPreviewStates.ready, onBack));

      const backBtn = document.querySelector<HTMLButtonElement>(".back-button");
      expect(backBtn).not.toBeNull();
      expect(backBtn?.getAttribute("aria-label")).toBe("Wróć do Dzisiaj");
      backBtn?.click();
      expect(onBack).toHaveBeenCalledOnce();
    });
  });

  describe("UX Hierarchy: Nutrition First, Calories Second", () => {
    it("renders coaching focus items and meal timeline before technical macros", () => {
      const element = renderNutritionExperience(nutritionPreviewStates.ready);

      const focusIndex = Array.from(element.children[0]?.children ?? []).findIndex(
        (child) => child.classList.contains("nutrition-focus-section"),
      );
      const techIndex = Array.from(element.children[0]?.children ?? []).findIndex(
        (child) => child.classList.contains("technical-metrics-section"),
      );

      expect(focusIndex).toBeGreaterThan(-1);
      expect(techIndex).toBeGreaterThan(-1);
      expect(focusIndex).toBeLessThan(techIndex);
    });

    it("renders meal timeline with 5 meals", () => {
      const element = renderNutritionExperience(nutritionPreviewStates.ready);
      const meals = element.querySelectorAll(".meal-card");
      expect(meals.length).toBe(5);
    });

    it("renders hydration bar with volume and percentage", () => {
      const element = renderNutritionExperience(nutritionPreviewStates.ready);
      const hydrationCard = element.querySelector(".hydration-card");
      expect(hydrationCard).not.toBeNull();
      expect(hydrationCard?.textContent).toContain("2.4L / 3.0L");
      expect(hydrationCard?.textContent).toContain("80% celu dziennego");
    });

    it("renders technical metrics at the bottom of the page", () => {
      const element = renderNutritionExperience(nutritionPreviewStates.ready);
      const techSection = element.querySelector(".technical-metrics-section");
      expect(techSection).not.toBeNull();

      const text = techSection?.textContent ?? "";
      expect(text).toContain("Energia (Kalorie)");
      expect(text).toContain("Węglowodany");
      expect(text).toContain("Białko");
      expect(text).toContain("Tłuszcze");
      expect(text).toContain("Błonnik");
      expect(text).toContain("Sód");
      expect(text).toContain("Potas");
    });
  });

  describe("Payload Mode Mapping", () => {
    it("maps valid fixture payload to nutrition ready state", () => {
      const result = parseAndMapAthleteDashboardToNutrition(payloadFixtures.ready, mockContext);
      expect(result.kind).toBe("ready");
      if (result.kind === "ready") {
        expect(result.nutrition.hero.headline).toContain("wspiera dzisiejszy trening");
        expect(result.nutrition.technical.metrics.length).toBeGreaterThan(0);
      }
    });

    it("maps stale payload date to stale state", () => {
      const result = mapAthleteDashboardToNutrition(
        {
          ...payloadFixtures.ready,
          valid_for_date: "2026-08-01",
        },
        mockContext,
      );
      expect(result.kind).toBe("stale");
    });
  });
});
