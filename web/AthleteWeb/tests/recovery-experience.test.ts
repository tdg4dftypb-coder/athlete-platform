import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApp, createRecoveryApp } from "../src/app/create-app";
import {
  resolveApplicationRecoveryState,
  resolveRecoveryPreviewState,
} from "../src/app/preview-state";
import {
  resolveApplicationView,
  searchForView,
} from "../src/app/view-routing";
import {
  partialPayloadFixture,
  readyPayloadFixture,
  recoveryUnavailablePayloadFixture,
} from "../src/fixtures/athlete-dashboard-payload-fixtures";
import { mapAthleteDashboardToRecovery } from "../src/mappers/recovery-mapper";
import { MORNING_BRIEFING_MAX_AGE_MS } from "../src/mappers/mapping-context";
import { morningBriefingPreviewStates } from "../src/preview-data/morning-briefing-preview-data";
import {
  recoveryPreviewData,
  recoveryPreviewStates,
} from "../src/preview-data/recovery-preview-data";

const mappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: MORNING_BRIEFING_MAX_AGE_MS,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
} as const;

describe("Recovery Experience", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("uses deterministic Preview Data explicitly separated from payload", () => {
    expect(recoveryPreviewData.source).toBe("preview");
    expect(recoveryPreviewData.hero.score).toBe(84);
    expect(Object.isFrozen(recoveryPreviewData)).toBe(true);
    expect(Object.isFrozen(recoveryPreviewData.factors)).toBe(true);
  });

  it("ready answers how recovery looks before showing factors and details", () => {
    document.body.append(createRecoveryApp(recoveryPreviewStates.ready));

    expect(document.querySelector("h1")?.textContent).toBe("Regeneracja");
    expect(document.querySelector("#recovery-status")?.textContent).toBe(
      "Dobra regeneracja",
    );
    expect(document.querySelector(".recovery-score")?.textContent).toContain("84");
    expect(Array.from(document.querySelectorAll("h2"), (heading) => heading.textContent)).toEqual([
      "Dobra regeneracja",
      "Najważniejsze czynniki",
      "Co to oznacza na dziś?",
      "Krótki trend",
      "Dane szczegółowe",
    ]);
    expect(document.querySelectorAll(".recovery-factor")).toHaveLength(4);
    expect(document.querySelector(".recovery-detail-list")?.textContent).toContain("Saturacja");
  });

  it("partial names missing data and never invents the missing HRV value", () => {
    document.body.append(createRecoveryApp(recoveryPreviewStates.partial));

    expect(document.querySelector(".state-detail-list")?.textContent).toContain("Brak HRV");
    expect(document.body.textContent).toContain("Wartość niedostępna");
    expect(document.body.textContent).not.toContain("0 ms");
  });

  it("unavailable explains the absence without showing a fake score", () => {
    document.body.append(createRecoveryApp(recoveryPreviewStates.unavailable));

    expect(document.querySelector(".state-message")?.textContent).toContain("nie jest teraz dostępna");
    expect(document.querySelector(".recovery-score")).toBeNull();
    expect(document.body.textContent).not.toContain("/100");
  });

  it("stale keeps content behind an explicit last-update warning", () => {
    document.body.append(createRecoveryApp(recoveryPreviewStates.stale));

    expect(document.querySelector(".state-notice--stale")).not.toBeNull();
    expect(document.body.textContent).toContain("Ostatnia aktualizacja: wczoraj, 21:45");
    expect(document.querySelector("#recovery-status")).not.toBeNull();
  });

  it("loading exposes aria-busy and a calm live status", () => {
    document.body.append(createRecoveryApp(recoveryPreviewStates.loading));

    expect(document.querySelector("main")?.getAttribute("aria-busy")).toBe("true");
    expect(document.querySelector('[role="status"]')?.textContent).toBe(
      "Przygotowujemy widok regeneracji.",
    );
    expect(document.querySelectorAll(".skeleton-block")).toHaveLength(4);
  });

  it("failure exposes a retry action", () => {
    const retry = vi.fn();
    document.body.append(createRecoveryApp(recoveryPreviewStates.failure, undefined, retry));

    const button = document.querySelector<HTMLButtonElement>(".primary-action");
    expect(button?.textContent).toBe("Spróbuj ponownie");
    button?.click();
    expect(retry).toHaveBeenCalledOnce();
  });

  it("opens Recovery from both Morning Briefing entry points", () => {
    const openRecovery = vi.fn();
    document.body.append(
      createApp(morningBriefingPreviewStates.ready, undefined, openRecovery),
    );

    document.querySelector<HTMLButtonElement>('[data-shortcut="recovery"]')?.click();
    document.querySelector<HTMLButtonElement>(".section-heading button")?.click();

    expect(openRecovery).toHaveBeenCalledTimes(2);
    expect(document.querySelector<HTMLButtonElement>('[data-shortcut="recovery"]')?.disabled).toBe(false);
  });

  it("returns from Recovery to Morning Briefing using an accessible back button", () => {
    const back = vi.fn();
    document.body.append(createRecoveryApp(recoveryPreviewStates.ready, back));

    const button = document.querySelector<HTMLButtonElement>('.back-button');
    expect(button?.getAttribute("aria-label")).toBe("Wróć do Dzisiaj");
    button?.click();
    expect(back).toHaveBeenCalledOnce();
  });

  it.each(["ready", "partial", "unavailable", "stale", "loading", "failure"] as const)(
    "query string selects Recovery %s",
    (kind) => {
      expect(resolveApplicationView(`?view=recovery&state=${kind}`)).toBe("recovery");
      expect(resolveRecoveryPreviewState(
        `?view=recovery&state=${kind}`,
        recoveryPreviewStates,
      ).kind).toBe(kind);
    },
  );

  it("unknown view falls back to Morning Briefing and URL helpers preserve state", () => {
    expect(resolveApplicationView("?view=unknown&state=partial")).toBe("morning-briefing");
    expect(searchForView("?state=partial", "recovery")).toBe("?state=partial&view=recovery");
    expect(searchForView("?view=recovery&state=partial", "morning-briefing")).toBe("?state=partial");
  });

  it("source=payload renders no Preview-only trends or historical comparisons", () => {
    const state = mapAthleteDashboardToRecovery(readyPayloadFixture, mappingContext);
    expect(state.kind).toBe("ready");
    if (state.kind !== "ready") throw new Error("Expected ready recovery state");
    expect(state.recovery.source).toBe("payload");
    expect(state.recovery.trendSummary).toBeNull();
    expect(state.recovery.factors.every((factor) => factor.trendText === null)).toBe(true);

    document.body.append(createRecoveryApp(state));
    expect(document.querySelector(".trend-indicator")).toBeNull();
    expect(document.querySelector(".recovery-trend-section")).toBeNull();
    expect(document.body.textContent).not.toContain("względem wczoraj");
  });

  it("payload missing values remain absent instead of becoming presentation values", () => {
    const state = mapAthleteDashboardToRecovery(partialPayloadFixture, mappingContext);
    expect(state.kind).toBe("partial");
    if (state.kind !== "partial") throw new Error("Expected partial recovery state");
    const hrv = state.recovery.factors.find((factor) => factor.id === "hrv");
    expect(hrv?.valueText).toBeNull();
    expect(hrv?.trendText).toBeNull();

    document.body.append(createRecoveryApp(state));
    expect(document.body.textContent).not.toContain("0 ms");
    expect(document.body.textContent).not.toContain("+7%");
  });

  it("payload unavailable state is driven by Recovery source availability", () => {
    const state = mapAthleteDashboardToRecovery(
      recoveryUnavailablePayloadFixture,
      mappingContext,
    );

    expect(state.kind).toBe("unavailable");
    document.body.append(createRecoveryApp(state));
    expect(document.querySelector(".recovery-score")).toBeNull();
  });

  it("application payload resolver uses the selected fixture without Preview fallbacks", () => {
    const state = resolveApplicationRecoveryState(
      "?view=recovery&source=payload&fixture=partial",
      recoveryPreviewStates,
      mappingContext,
    );

    expect(state.kind).toBe("partial");
    if (state.kind !== "partial") throw new Error("Expected partial recovery state");
    expect(state.recovery.source).toBe("payload");
    expect(state.recovery.trendSummary).toBeNull();
  });
});
