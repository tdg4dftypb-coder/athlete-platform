import { describe, expect, it } from "vitest";
import {
  createIcon,
  mapActivityToIcon,
  type ActivityIconName,
  type IconName,
} from "../src/components/icon";
import { renderMorningBriefing } from "../src/features/morning-briefing/morning-briefing-view";
import type { MorningBriefingPresentationState } from "../src/models/morning-briefing-presentation-state";

describe("Activity Icon System", () => {
  const activityIcons: readonly ActivityIconName[] = [
    "activity-cycling",
    "activity-indoor-cycling",
    "activity-swimming",
    "activity-crossfit",
    "activity-gravel",
  ];

  it("renders SVG elements for all 5 activity icon names", () => {
    for (const iconName of activityIcons) {
      const svg = createIcon(iconName);
      expect(svg).toBeInstanceOf(SVGSVGElement);
      expect(svg.classList.contains("icon")).toBe(true);
      expect(svg.getAttribute("viewBox")).toBe("0 0 24 24");
      expect(svg.querySelectorAll("path").length).toBeGreaterThan(0);
    }
  });

  it("handles unknown icon names gracefully without throwing an error", () => {
    // Cast an unknown string to IconName
    const svg = createIcon("unknown-icon" as IconName);
    expect(svg).toBeInstanceOf(SVGSVGElement);
    expect(svg.querySelectorAll("path").length).toBeGreaterThan(0);
  });

  it("sets aria-hidden='true' for decorative icons without a label", () => {
    const svg = createIcon("activity-cycling");
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.hasAttribute("role")).toBe(false);
  });

  it("sets role='img' and aria-label for standalone icons with a label", () => {
    const svg = createIcon("activity-cycling", "Kolarstwo szosowe");
    expect(svg.getAttribute("role")).toBe("img");
    expect(svg.getAttribute("aria-label")).toBe("Kolarstwo szosowe");
    expect(svg.hasAttribute("aria-hidden")).toBe(false);
  });

  describe("mapActivityToIcon", () => {
    it("maps cycling / road to activity-cycling", () => {
      expect(mapActivityToIcon("cycling")).toBe("activity-cycling");
      expect(mapActivityToIcon("road cycling")).toBe("activity-cycling");
      expect(mapActivityToIcon("kolarstwo szosowe")).toBe("activity-cycling");
    });

    it("maps indoor cycling / trainer / zwift to activity-indoor-cycling", () => {
      expect(mapActivityToIcon("indoor cycling")).toBe("activity-indoor-cycling");
      expect(mapActivityToIcon("trainer")).toBe("activity-indoor-cycling");
      expect(mapActivityToIcon("Zwift Endurance")).toBe("activity-indoor-cycling");
      expect(mapActivityToIcon("Próg 3x10 min (Trenażer)")).toBe("activity-indoor-cycling");
    });

    it("maps swimming to activity-swimming", () => {
      expect(mapActivityToIcon("swimming")).toBe("activity-swimming");
      expect(mapActivityToIcon("pływanie kraulem")).toBe("activity-swimming");
    });

    it("maps crossfit / functional strength to activity-crossfit", () => {
      expect(mapActivityToIcon("crossfit")).toBe("activity-crossfit");
      expect(mapActivityToIcon("functional strength")).toBe("activity-crossfit");
      expect(mapActivityToIcon("trening siłowy")).toBe("activity-crossfit");
    });

    it("maps gravel / mountain biking to activity-gravel", () => {
      expect(mapActivityToIcon("gravel")).toBe("activity-gravel");
      expect(mapActivityToIcon("mountain biking")).toBe("activity-gravel");
      expect(mapActivityToIcon("jazda terenowa MTB")).toBe("activity-gravel");
    });

    it("maps running to runner", () => {
      expect(mapActivityToIcon("running")).toBe("runner");
      expect(mapActivityToIcon("bieg progowy")).toBe("runner");
    });

    it("defaults to activity-cycling when activityType is undefined, null, or empty", () => {
      expect(mapActivityToIcon()).toBe("activity-cycling");
      expect(mapActivityToIcon(null)).toBe("activity-cycling");
      expect(mapActivityToIcon("")).toBe("activity-cycling");
    });
  });

  describe("UI Integration", () => {
    it("renders cycling/indoor-cycling icon in decision card for bike workout instead of old runner icon", () => {
      const state: MorningBriefingPresentationState = {
        kind: "ready",
        briefing: {
          greeting: "Dzień dobry",
          athleteName: "Marcin",
          dateText: "Poniedziałek, 3 sierpnia",
          timeText: "08:00",
          coachMessage: ["Dzisiejsza decyzja to jazda progowa na trenażerze."],
          decision: {
            title: "Threshold 45 (Zwift)",
            duration: "45 minut",
            intensity: "Próg",
          },
          reasons: ["HRV w normie"],
          changesSinceYesterday: [],
          todayPlan: ["Threshold 45 (Zwift)"],
          goal: {
            title: "Masa docelowa 77 kg",
            progressAccessibilityLabel: "Kompletność celu",
            progressLabel: "75% danych",
            progressValue: 0.75,
            timeline: "1 lip – 1 paź 2026",
          },
          shortcuts: [
            { id: "recovery", label: "Regeneracja" },
            { id: "training", label: "Trening" },
          ],
        },
      };

      const element = renderMorningBriefing(state, () => undefined);
      const decisionBadge = element.querySelector(".decision-summary .icon-badge");
      expect(decisionBadge).not.toBeNull();

      // Check that the icon contains path data for activity-indoor-cycling, not runner
      const paths = Array.from(decisionBadge!.querySelectorAll("path")).map((p) => p.getAttribute("d"));
      const isIndoorCycling = paths.some((d) => d?.includes("20h20") || d?.includes("15.5 17"));
      expect(isIndoorCycling).toBe(true);
    });
  });
});
