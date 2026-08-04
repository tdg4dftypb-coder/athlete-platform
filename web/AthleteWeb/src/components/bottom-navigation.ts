import { createIcon, type IconName } from "./icon";
import type { ApplicationView } from "../app/view-routing";

export interface BottomNavigationOptions {
  readonly currentView?: ApplicationView;
  readonly onNavigate?: (view: ApplicationView) => void;
  readonly onOpenMorning?: () => void;
  readonly onOpenTraining?: () => void;
  readonly onOpenProgress?: () => void;
  readonly onOpenMore?: () => void;
}

const navigationItems: readonly {
  id: "morning" | "training" | "progress" | "more";
  label: string;
  icon: IconName;
  targetView: "morning" | "training" | "progress" | "more";
}[] = [
  { id: "morning", label: "Dzisiaj", icon: "sun", targetView: "morning" },
  { id: "training", label: "Trening", icon: "activity-cycling", targetView: "training" },
  { id: "progress", label: "Postępy", icon: "chart", targetView: "progress" },
  { id: "more", label: "Więcej", icon: "more", targetView: "more" },
];

export function createBottomNavigation(
  optionsOrTraining?: BottomNavigationOptions | (() => void),
  onOpenProgressLegacy?: () => void,
): HTMLElement {
  let activeView: ApplicationView = "morning";
  let navigateHandler: ((view: ApplicationView) => void) | undefined;
  let onOpenTraining: (() => void) | undefined;
  let onOpenProgress: (() => void) | undefined;

  if (typeof optionsOrTraining === "object" && optionsOrTraining !== null) {
    activeView = optionsOrTraining.currentView ?? "morning";
    navigateHandler = optionsOrTraining.onNavigate;
    onOpenTraining = optionsOrTraining.onOpenTraining;
    onOpenProgress = optionsOrTraining.onOpenProgress;
  } else if (typeof optionsOrTraining === "function") {
    onOpenTraining = optionsOrTraining;
    onOpenProgress = onOpenProgressLegacy;
  }

  const nav = document.createElement("nav");
  nav.className = "bottom-navigation";
  nav.setAttribute("aria-label", "Główna nawigacja");

  for (const item of navigationItems) {
    const button = document.createElement("button");
    button.type = "button";

    const isActive =
      (item.id === "morning" && (activeView === "morning" || activeView === "morning-briefing")) ||
      (item.id === "training" && activeView === "training") ||
      (item.id === "progress" && activeView === "progress") ||
      (item.id === "more" && (activeView === "more" || activeView === "recovery" || activeView === "nutrition" || activeView === "body"));

    button.className = isActive ? "is-active" : "";
    button.disabled = false;
    button.setAttribute("aria-current", isActive ? "page" : "false");
    button.setAttribute("aria-label", `Przejdź do: ${item.label}`);

    button.addEventListener("click", () => {
      if (item.id === "training" && onOpenTraining) {
        onOpenTraining();
        return;
      }
      if (item.id === "progress" && onOpenProgress) {
        onOpenProgress();
        return;
      }
      if (navigateHandler) {
        navigateHandler(item.targetView);
        return;
      }

      const url = new URL(window.location.href);
      url.searchParams.set("view", item.targetView);
      window.history.pushState({ athleteView: item.targetView }, "", url);
      window.dispatchEvent(new Event("popstate"));
    });

    button.append(createIcon(item.icon), document.createTextNode(item.label));
    nav.append(button);
  }

  return nav;
}
