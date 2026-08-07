import { describe, expect, it, vi } from "vitest";
import { createBottomNavigation } from "../src/components/bottom-navigation";
import { resolveApplicationView, searchForView } from "../src/app/view-routing";

describe("Bottom Navigation Routing", () => {
  it("renders all 4 tabs enabled and clickable", () => {
    const nav = createBottomNavigation({ currentView: "morning" });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    expect(buttons.length).toBe(4);
    buttons.forEach((btn) => {
      expect(btn.disabled).toBe(false);
    });

    const labels = Array.from(buttons).map((btn) => btn.textContent?.trim());
    expect(labels).toEqual(["Dzisiaj", "Trening", "Postępy", "Więcej"]);
  });

  it("marks 'Dzisiaj' as active when currentView is morning", () => {
    const nav = createBottomNavigation({ currentView: "morning" });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    expect(buttons[0]?.classList.contains("is-active")).toBe(true);
    expect(buttons[0]?.getAttribute("aria-current")).toBe("page");

    expect(buttons[1]?.classList.contains("is-active")).toBe(false);
    expect(buttons[2]?.classList.contains("is-active")).toBe(false);
    expect(buttons[3]?.classList.contains("is-active")).toBe(false);
  });

  it("marks 'Trening' as active when currentView is training", () => {
    const nav = createBottomNavigation({ currentView: "training" });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    expect(buttons[1]?.classList.contains("is-active")).toBe(true);
    expect(buttons[1]?.getAttribute("aria-current")).toBe("page");
  });

  it("marks 'Postępy' as active when currentView is progress", () => {
    const nav = createBottomNavigation({ currentView: "progress" });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    expect(buttons[2]?.classList.contains("is-active")).toBe(true);
    expect(buttons[2]?.getAttribute("aria-current")).toBe("page");
  });

  it("marks 'Więcej' as active when currentView is more, recovery, nutrition, or body", () => {
    for (const view of ["more", "recovery", "nutrition", "body"] as const) {
      const nav = createBottomNavigation({ currentView: view });
      const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

      expect(buttons[3]?.classList.contains("is-active")).toBe(true);
      expect(buttons[3]?.getAttribute("aria-current")).toBe("page");
    }
  });

  it("marks 'Dzisiaj' as active for Morning Briefing detail", () => {
    const nav = createBottomNavigation({ currentView: "morning-briefing-detail" });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    expect(buttons[0]?.classList.contains("is-active")).toBe(true);
    expect(buttons[0]?.getAttribute("aria-current")).toBe("page");
  });

  it("marks 'Więcej' as active for nested More experiences", () => {
    for (const view of [
      "biomarkers",
      "history",
      "performance-lab",
      "performance-lab-detail",
      "ai-coach",
      "icons",
    ] as const) {
      const nav = createBottomNavigation({ currentView: view });
      const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

      expect(buttons[3]?.classList.contains("is-active")).toBe(true);
      expect(buttons[3]?.getAttribute("aria-current")).toBe("page");
    }
  });

  it("triggers navigate callbacks for tabs", () => {
    const onNavigate = vi.fn();
    const nav = createBottomNavigation({ currentView: "morning", onNavigate });
    const buttons = nav.querySelectorAll<HTMLButtonElement>("button");

    buttons[1]?.click(); // Trening
    expect(onNavigate).toHaveBeenLastCalledWith("training");

    buttons[2]?.click(); // Postępy
    expect(onNavigate).toHaveBeenLastCalledWith("progress");

    buttons[3]?.click(); // Więcej
    expect(onNavigate).toHaveBeenLastCalledWith("more");

    buttons[0]?.click(); // Dzisiaj
    expect(onNavigate).toHaveBeenLastCalledWith("morning");
  });

  it("resolves view routing correctly for all views", () => {
    expect(resolveApplicationView("?view=morning")).toBe("morning-briefing");
    expect(resolveApplicationView("?view=training")).toBe("training");
    expect(resolveApplicationView("?view=progress")).toBe("progress");
    expect(resolveApplicationView("?view=more")).toBe("more");
    expect(resolveApplicationView("?view=recovery")).toBe("recovery");
    expect(resolveApplicationView("?view=nutrition")).toBe("nutrition");
    expect(resolveApplicationView("?view=body")).toBe("body");
  });

  it("preserves query parameters when updating view in searchForView", () => {
    const search = "?state=ready&source=payload";
    expect(searchForView(search, "training")).toBe("?state=ready&source=payload&view=training");
    expect(searchForView(search, "progress")).toBe("?state=ready&source=payload&view=progress");
    expect(searchForView(search, "more")).toBe("?state=ready&source=payload&view=more");
    expect(searchForView(search, "morning")).toBe("?state=ready&source=payload");
  });
});

