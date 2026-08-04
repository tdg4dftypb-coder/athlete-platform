import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApp } from "../src/app/create-app";
import { resolvePreviewState } from "../src/app/preview-state";
import {
  morningBriefingPreviewData,
  morningBriefingPreviewStates,
} from "../src/preview-data/morning-briefing-preview-data";

describe("Morning Briefing", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("uses deterministic and immutable Preview Data", () => {
    expect(morningBriefingPreviewData.timeText).toBe("07:30");
    expect(morningBriefingPreviewData.goal.progressValue).toBe(0.75);
    expect(Object.isFrozen(morningBriefingPreviewData)).toBe(true);
    expect(Object.isFrozen(morningBriefingPreviewData.coachMessage)).toBe(true);
  });

  it("ready renders every main section", () => {
    const app = createApp(morningBriefingPreviewStates.ready);
    document.body.append(app);

    expect(document.querySelector("h1")?.textContent).toBe("Dzień dobry, Marcin!");
    expect(Array.from(document.querySelectorAll("h2"), (heading) => heading.textContent)).toEqual([
      "Dzień zapowiada się bardzo dobrze.",
      "Dzisiejsza decyzja",
      "Dlaczego właśnie taki plan?",
      "Co zmieniło się od wczoraj?",
      "Plan na dziś",
      "Twój cel",
      "Dowiedz się więcej",
    ]);
    expect(document.querySelector(".hero-card")?.textContent).toContain("Dzisiaj warto wykonać trening progowy.");
    expect(document.querySelector(".hero-card")?.textContent).not.toContain("AI Coach");
    expect(document.querySelector(".decision-details")?.textContent).toBe("60–75 min • Strefa 3–4");
    expect(document.querySelector('[role="progressbar"]')?.getAttribute("aria-label")).toBe("Postęp celu");
    expect(document.querySelectorAll(".shortcut-grid li")).toHaveLength(4);
    expect(document.querySelector<HTMLButtonElement>(".listen-button")?.disabled).toBe(true);
    expect(document.querySelectorAll(".bottom-navigation .icon")).toHaveLength(4);
  });

  it("marks only Dzisiaj as the active navigation tab", () => {
    document.body.append(createApp(morningBriefingPreviewStates.ready));

    const current = document.querySelectorAll('.bottom-navigation [aria-current="page"]');
    expect(current).toHaveLength(1);
    expect(current[0]?.textContent).toContain("Dzisiaj");
    expect(document.querySelectorAll(".bottom-navigation button:not(:disabled)")).toHaveLength(4);
  });


  it("partial names missing data and omits unsupported reasons", () => {
    document.body.append(createApp(morningBriefingPreviewStates.partial));

    expect(document.querySelector(".state-message")?.textContent).toContain("niepełnych danych");
    expect(document.querySelector(".state-detail-list")?.textContent).toContain("Brak HRV");
    expect(document.querySelector(".state-detail-list")?.textContent).toContain("Brak danych snu");
    expect(document.querySelector(".reason-region")?.textContent).not.toContain("HRV wróciło do normy");
  });

  it("does not attach Preview-only comparisons to an unknown payload reason", () => {
    document.body.append(createApp({
      kind: "ready",
      briefing: {
        ...morningBriefingPreviewData,
        reasons: ["Plan treningowy jest realizowany regularnie"],
        changesSinceYesterday: [],
        goal: {
          ...morningBriefingPreviewData.goal,
          progressLabel: "Postęp niedostępny",
          progressValue: null,
        },
      },
    }));

    expect(document.querySelector(".reason-region")?.textContent).not.toContain("Lepsze o 7%");
    expect(document.querySelector(".changes-card")).toBeNull();
    expect(document.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow")).toBeNull();
  });

  it("unavailable explains the absence and does not render a decision", () => {
    document.body.append(createApp(morningBriefingPreviewStates.unavailable));

    expect(document.querySelector(".state-message")?.textContent).toContain("wystarczających danych");
    expect(document.querySelector("#today-decision")).toBeNull();
    expect(document.body.textContent).toContain("Sprawdź ponownie po kolejnej synchronizacji danych.");
  });

  it("stale keeps the briefing behind an explicit update warning", () => {
    document.body.append(createApp(morningBriefingPreviewStates.stale));

    expect(document.querySelector(".state-message")?.textContent).toContain("danych z wczoraj");
    expect(document.body.textContent).toContain("Ostatnia aktualizacja: wczoraj, 21:45");
    expect(document.querySelector("#today-decision")).not.toBeNull();
  });

  it("loading exposes a calm busy state", () => {
    document.body.append(createApp(morningBriefingPreviewStates.loading));

    expect(document.querySelector("main")?.getAttribute("aria-busy")).toBe("true");
    expect(document.querySelector('[role="status"]')?.textContent).toBe("Przygotowujemy poranną odprawę.");
    expect(document.querySelectorAll(".skeleton-block").length).toBeGreaterThan(0);
  });

  it("failure exposes a retry action", () => {
    const retry = vi.fn();
    document.body.append(createApp(morningBriefingPreviewStates.failure, retry));

    const button = document.querySelector<HTMLButtonElement>(".primary-action");
    expect(document.querySelector(".state-message")?.textContent).toContain("Nie udało się teraz odświeżyć");
    expect(button?.textContent).toBe("Spróbuj ponownie");
    button?.click();
    expect(retry).toHaveBeenCalledOnce();
  });

  it.each(["partial", "unavailable", "stale", "failure"] as const)(
    "%s exposes its semantic visual variant",
    (kind) => {
      document.body.append(createApp(morningBriefingPreviewStates[kind]));

      expect(document.querySelector(`.state-notice--${kind}`)).not.toBeNull();
    },
  );

  it.each(["ready", "partial", "unavailable", "stale", "loading", "failure"] as const)(
    "query string selects the %s state",
    (kind) => {
      expect(resolvePreviewState(`?state=${kind}`, morningBriefingPreviewStates).kind).toBe(kind);
    },
  );

  it("an invalid query string safely falls back to ready", () => {
    expect(resolvePreviewState("?state=unknown", morningBriefingPreviewStates)).toBe(
      morningBriefingPreviewStates.ready,
    );
  });

  it("uses ready when the query string does not select a state", () => {
    expect(resolvePreviewState("", morningBriefingPreviewStates)).toBe(
      morningBriefingPreviewStates.ready,
    );
  });
});
