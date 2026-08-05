import { describe, expect, it, vi } from "vitest";
import {
  parseAndMapAthleteDashboardToTraining,
  mapAthleteDashboardToTraining,
} from "../src/mappers/training-mapper";
import { createTrainingApp } from "../src/app/create-app";
import { renderTrainingExperience } from "../src/features/training/training-view";

import { resolveApplicationView } from "../src/app/view-routing";
import { resolveTrainingPreviewState } from "../src/app/preview-state";
import { trainingPreviewStates } from "../src/preview-data/training-preview-data";
import { payloadFixtures } from "../src/fixtures/athlete-dashboard-payload-fixtures";
import type { MappingContext } from "../src/mappers/mapping-context";

const mockContext: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 24 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("Training Experience", () => {
  describe("State Rendering", () => {
    it("renders ready state with hero, objective, structure, notes, outcome, and technical details", () => {
      const state = trainingPreviewStates.ready;
      const element = renderTrainingExperience(state);

      expect(element.querySelector("h1")?.textContent).toBe("Trening");
      expect(element.querySelector(".training-hero__title")?.textContent).toBe("Threshold 45 (Zwift)");
      expect(element.querySelector(".objective-text")?.textContent).toContain("wytrzymałość progową");
      expect(element.querySelectorAll(".workout-block-item").length).toBe(3);
      expect(element.querySelectorAll(".note-item").length).toBe(4);
      expect(element.querySelector(".outcome-text")?.textContent).toContain("umiarkowane zmęczenie nóg");
      expect(element.querySelector(".technical-grid")).not.toBeNull();
    });

    it("renders partial state with status notice detailing missing items", () => {
      const state = trainingPreviewStates.partial;
      const element = renderTrainingExperience(state);

      const notice = element.querySelector(".state-notice--partial");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Niepełne dane");
      expect(notice?.textContent).toContain("Brak przewidywanego IF");
    });

    it("renders unavailable state with unavailability notice and reason", () => {
      const state = trainingPreviewStates.unavailable;
      const element = renderTrainingExperience(state);

      const notice = element.querySelector(".state-notice--unavailable");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Trening jest dziś niedostępny");
      expect(notice?.textContent).toContain("dzień pełnej regeneracji");
    });

    it("renders stale state with staleness notice and last updated text", () => {
      const state = trainingPreviewStates.stale;
      const element = renderTrainingExperience(state);

      const notice = element.querySelector(".state-notice--stale");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Dane wymagają odświeżenia");
      expect(notice?.textContent).toContain("wczoraj, 18:30");
    });

    it("renders loading state with skeleton layout and aria-busy='true'", () => {
      const state = trainingPreviewStates.loading;
      const element = renderTrainingExperience(state);

      const main = element.querySelector("main");
      expect(main?.getAttribute("aria-busy")).toBe("true");
      expect(element.querySelector(".loading-label")?.textContent).toContain("Trwa przygotowywanie");
      expect(element.querySelectorAll(".skeleton-block").length).toBeGreaterThan(0);
    });

    it("renders failure state with retry button", () => {
      const onRetry = vi.fn();
      const state = trainingPreviewStates.failure;
      const element = renderTrainingExperience(state, () => undefined, onRetry);

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
    it("resolves view=training to training", () => {
      expect(resolveApplicationView("?view=training")).toBe("training");
      expect(resolveApplicationView("?view=training&state=partial")).toBe("training");
    });

    it("resolves preview state by query parameter", () => {
      expect(resolveTrainingPreviewState("?state=partial", trainingPreviewStates).kind).toBe("partial");
      expect(resolveTrainingPreviewState("?state=unavailable", trainingPreviewStates).kind).toBe("unavailable");
      expect(resolveTrainingPreviewState("?state=stale", trainingPreviewStates).kind).toBe("stale");
      expect(resolveTrainingPreviewState("?state=loading", trainingPreviewStates).kind).toBe("loading");
      expect(resolveTrainingPreviewState("?state=failure", trainingPreviewStates).kind).toBe("failure");
      expect(resolveTrainingPreviewState("", trainingPreviewStates).kind).toBe("ready");
    });

    it("triggers back navigation callback when back button is clicked", () => {
      document.body.replaceChildren();
      const onBack = vi.fn();
      document.body.append(createTrainingApp(trainingPreviewStates.ready, onBack));

      const backBtn = document.querySelector<HTMLButtonElement>(".back-button");
      expect(backBtn).not.toBeNull();
      expect(backBtn?.getAttribute("aria-label")).toBe("Wróć do Dzisiaj");
      backBtn?.click();
      expect(onBack).toHaveBeenCalledOnce();
    });

  });

  describe("Progressive Disclosure & Component Hierarchy", () => {
    it("renders Hero card without raw IF/TSS metrics", () => {
      const element = renderTrainingExperience(trainingPreviewStates.ready);
      const heroPillsText = element.querySelector(".training-hero__pills")?.textContent ?? "";

      expect(heroPillsText).toContain("45 min");
      expect(heroPillsText).toContain("Próg");
      expect(heroPillsText).not.toContain("0.85 IF");
      expect(heroPillsText).not.toContain("54 TSS");
    });

    it("renders workout blocks with step connectors", () => {
      const element = renderTrainingExperience(trainingPreviewStates.ready);
      const blocks = element.querySelectorAll(".workout-block-item");
      const connectors = element.querySelectorAll(".workout-block__connector");

      expect(blocks.length).toBe(3);
      expect(connectors.length).toBe(2);
      expect(connectors[0]?.textContent).toBe("↓");
    });

    it("renders technical details at the bottom of the screen", () => {
      const element = renderTrainingExperience(trainingPreviewStates.ready);
      const techSection = element.querySelector(".technical-details-section");
      expect(techSection).not.toBeNull();

      const techText = techSection?.textContent ?? "";
      expect(techText).toContain("0.85 IF");
      expect(techText).toContain("54 TSS");
      expect(techText).toContain("245 W");
      expect(techText).toContain("520 kcal");
    });
  });

  describe("Payload Mode Mapping", () => {
    it("maps valid fixture payload to training ready state", () => {
      const result = parseAndMapAthleteDashboardToTraining(payloadFixtures.ready, mockContext);
      expect(result.kind).toBe("ready");
      if (result.kind === "ready") {
        expect(result.training.hero.title).toBe("Trening progowy");
        expect(result.training.hero.activityIcon).toBe("activity-cycling");
        expect(result.training.technicalDetails?.tss).toBe("62 TSS");
      }
    });

    it("maps partial payload without inventing fake data for missing fields", () => {
      const result = parseAndMapAthleteDashboardToTraining(payloadFixtures.partial, mockContext);
      expect(result.kind).toBe("ready");
      if (result.kind === "ready") {
        expect(result.training.source).toBe("payload");
      }
    });

    it("maps unavailable training payload to unavailable state", () => {
      const result = parseAndMapAthleteDashboardToTraining(payloadFixtures.unavailable, mockContext);
      expect(result.kind).toBe("unavailable");
    });

    it("does not output 'null' or 'undefined' text when rendering partial training", () => {
      const state = parseAndMapAthleteDashboardToTraining(payloadFixtures.partial, mockContext);
      const element = renderTrainingExperience(state);
      const text = element.textContent ?? "";
      expect(text).not.toContain("null");
      expect(text).not.toContain("undefined");
    });

    it("maps stale payload date to stale state", () => {
      const result = mapAthleteDashboardToTraining(
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
