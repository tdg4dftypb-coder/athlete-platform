import { describe, expect, it, vi } from "vitest";
import {
  parseAndMapAthleteDashboardToProgress,
  mapAthleteDashboardToProgress,
} from "../src/mappers/progress-mapper";
import { renderProgressExperience } from "../src/features/progress/progress-view";
import { createProgressApp } from "../src/app/create-app";
import { resolveApplicationView } from "../src/app/view-routing";
import { resolveProgressPreviewState } from "../src/app/preview-state";
import { progressPreviewStates } from "../src/preview-data/progress-preview-data";
import { payloadFixtures } from "../src/fixtures/athlete-dashboard-payload-fixtures";
import type { MappingContext } from "../src/mappers/mapping-context";

const mockContext: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 24 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("Progress Experience", () => {
  describe("State Rendering", () => {
    it("renders ready state with hero, improvements, areas to improve, trend, ai summary, and technical metrics", () => {
      const state = progressPreviewStates.ready;
      const element = renderProgressExperience(state);

      expect(element.querySelector("h1")?.textContent).toBe("Postępy");
      expect(element.querySelector(".progress-hero__headline")?.textContent).toContain("systematycznie rośnie");
      expect(element.querySelectorAll(".improvement-card-item").length).toBe(4);
      expect(element.querySelectorAll(".area-card-item").length).toBeLessThanOrEqual(3);
      expect(element.querySelector(".progress-trend-section")).not.toBeNull();
      expect(element.querySelector(".ai-summary-section")).not.toBeNull();
      expect(element.querySelector(".technical-metrics-section")).not.toBeNull();
    });

    it("renders partial state with status notice detailing missing items", () => {
      const state = progressPreviewStates.partial;
      const element = renderProgressExperience(state);

      const notice = element.querySelector(".state-notice--partial");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Częściowe dane");
    });

    it("renders unavailable state with unavailability notice and reason", () => {
      const state = progressPreviewStates.unavailable;
      const element = renderProgressExperience(state);

      const notice = element.querySelector(".state-notice--unavailable");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("niedostępna");
    });

    it("renders stale state with staleness notice and last updated text", () => {
      const state = progressPreviewStates.stale;
      const element = renderProgressExperience(state);

      const notice = element.querySelector(".state-notice--stale");
      expect(notice).not.toBeNull();
      expect(notice?.textContent).toContain("Dane wymagają odświeżenia");
    });

    it("renders loading state with skeleton layout and aria-busy='true'", () => {
      const state = progressPreviewStates.loading;
      const element = renderProgressExperience(state);

      const main = element.querySelector("main");
      expect(main?.getAttribute("aria-busy")).toBe("true");
      expect(element.querySelector(".loading-label")?.textContent).toContain("Trwa analizowanie");
      expect(element.querySelectorAll(".skeleton-block").length).toBeGreaterThan(0);
    });

    it("renders failure state with retry button", () => {
      const onRetry = vi.fn();
      const state = progressPreviewStates.failure;
      const element = renderProgressExperience(state, () => undefined, onRetry);

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
    it("resolves view=progress to progress", () => {
      expect(resolveApplicationView("?view=progress")).toBe("progress");
      expect(resolveApplicationView("?view=progress&state=partial")).toBe("progress");
    });

    it("resolves preview state by query parameter", () => {
      expect(resolveProgressPreviewState("?state=partial", progressPreviewStates).kind).toBe("partial");
      expect(resolveProgressPreviewState("?state=unavailable", progressPreviewStates).kind).toBe("unavailable");
      expect(resolveProgressPreviewState("?state=stale", progressPreviewStates).kind).toBe("stale");
      expect(resolveProgressPreviewState("?state=loading", progressPreviewStates).kind).toBe("loading");
      expect(resolveProgressPreviewState("?state=failure", progressPreviewStates).kind).toBe("failure");
      expect(resolveProgressPreviewState("", progressPreviewStates).kind).toBe("ready");
    });

    it("triggers back navigation callback when back button is clicked", () => {
      document.body.replaceChildren();
      const onBack = vi.fn();
      document.body.append(createProgressApp(progressPreviewStates.ready, onBack));

      const backBtn = document.querySelector<HTMLButtonElement>(".back-button");
      expect(backBtn).not.toBeNull();
      expect(backBtn?.getAttribute("aria-label")).toBe("Wróć do Dzisiaj");
      backBtn?.click();
      expect(onBack).toHaveBeenCalledOnce();
    });
  });

  describe("Progressive Disclosure & Component Hierarchy", () => {
    it("renders Hero progress card with narrative before charts", () => {
      const element = renderProgressExperience(progressPreviewStates.ready);
      const heroText = element.querySelector(".progress-hero-card")?.textContent ?? "";

      expect(heroText).toContain("Twoja forma systematycznie rośnie.");
      expect(heroText).toContain("Forma zwyżkowa");
      expect(element.querySelector(".progress-hero-card .sparkline-container")).toBeNull();
    });

    it("renders 3-4 biggest improvement cards", () => {
      const element = renderProgressExperience(progressPreviewStates.ready);
      const cards = element.querySelectorAll(".improvement-card");
      expect(cards.length).toBeGreaterThanOrEqual(3);
      expect(cards.length).toBeLessThanOrEqual(4);
    });

    it("renders areas to improve with coaching tone tags", () => {
      const element = renderProgressExperience(progressPreviewStates.ready);
      const cards = element.querySelectorAll(".area-card");
      expect(cards.length).toBeLessThanOrEqual(3);
      expect(element.querySelector(".area-card__tag")?.textContent).toBe("Regeneracja");
    });

    it("renders minimalist sparkline trend section", () => {
      const element = renderProgressExperience(progressPreviewStates.ready);
      const sparkline = element.querySelector(".sparkline-bars");
      expect(sparkline).not.toBeNull();
      expect(sparkline?.querySelectorAll(".sparkline-col").length).toBe(6);
    });

    it("renders technical metrics at the bottom of the screen", () => {
      const element = renderProgressExperience(progressPreviewStates.ready);
      const techSection = element.querySelector(".technical-metrics-section");
      expect(techSection).not.toBeNull();

      const text = techSection?.textContent ?? "";
      expect(text).toContain("Kondycja (CTL / Fitness)");
      expect(text).toContain("Forma (TSB / Form)");
      expect(text).toContain("Aktualna masa ciała");
    });
  });


  describe("Payload Mode Mapping", () => {
    it("maps valid fixture payload to progress ready state", () => {
      const result = parseAndMapAthleteDashboardToProgress(payloadFixtures.ready, mockContext);
      expect(result.kind).toBe("ready");
      if (result.kind === "ready") {
        expect(result.progress.hero.headline).toContain("Twoja forma");
        expect(result.progress.technicalMetrics.metrics.length).toBeGreaterThan(0);
      }
    });

    it("maps stale payload date to stale state", () => {
      const result = mapAthleteDashboardToProgress(
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
