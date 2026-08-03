import { beforeEach, describe, expect, it } from "vitest";

import { createApp } from "../src/app/create-app";
import { morningBriefingPreviewData } from "../src/preview-data/morning-briefing-preview-data";

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

  it("renders every main section", () => {
    const app = createApp(morningBriefingPreviewData);
    document.body.append(app);

    expect(document.querySelector("h1")?.textContent).toBe("Dzień dobry, Marcin.");
    expect(Array.from(document.querySelectorAll("h2"), (heading) => heading.textContent)).toEqual([
      "Dzisiejsza decyzja",
      "Dlaczego właśnie taki plan?",
      "Co zmieniło się od wczoraj?",
      "Plan na dziś",
      "Twój cel",
      "Skróty",
    ]);
    expect(document.querySelector(".hero-card")?.textContent).toContain("Dzisiaj warto wykonać trening progowy.");
    expect(document.querySelector(".hero-card")?.textContent).not.toContain("AI Coach");
    expect(document.querySelector(".decision-details")?.textContent).toBe("60–75 minut • Strefa 3–4");
    expect(document.querySelectorAll(".shortcut-list li")).toHaveLength(4);
  });

  it("marks only Dzisiaj as the active navigation tab", () => {
    document.body.append(createApp(morningBriefingPreviewData));

    const current = document.querySelectorAll('.bottom-navigation [aria-current="page"]');
    expect(current).toHaveLength(1);
    expect(current[0]?.textContent).toContain("Dzisiaj");
    expect(document.querySelectorAll(".bottom-navigation button:not(:disabled)")).toHaveLength(1);
  });
});
