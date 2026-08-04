import { createIcon, type IconName } from "./icon";

const navigationItems: readonly { label: string; icon: IconName }[] = [
  { label: "Dzisiaj", icon: "sun" },
  { label: "Trening", icon: "activity-cycling" },
  { label: "Postępy", icon: "chart" },
  { label: "Więcej", icon: "more" },
];

export function createBottomNavigation(
  onOpenTraining?: () => void,
  onOpenProgress?: () => void,
): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = "bottom-navigation";
  nav.setAttribute("aria-label", "Główna nawigacja");
  for (const item of navigationItems) {
    const button = document.createElement("button");
    const isToday = item.label === "Dzisiaj";
    const isTraining = item.label === "Trening" && Boolean(onOpenTraining);
    const isProgress = item.label === "Postępy" && Boolean(onOpenProgress);
    const isEnabled = isToday || isTraining || isProgress;

    button.type = "button";
    button.className = isToday ? "is-active" : "";
    button.disabled = !isEnabled;
    button.setAttribute("aria-current", isToday ? "page" : "false");

    if (isTraining && onOpenTraining) {
      button.setAttribute("aria-label", "Otwórz ekran treningu");
      button.addEventListener("click", onOpenTraining);
    } else if (isProgress && onOpenProgress) {
      button.setAttribute("aria-label", "Otwórz ekran postępów");
      button.addEventListener("click", onOpenProgress);
    } else if (!isToday) {
      button.setAttribute("aria-label", `${item.label}, funkcja niedostępna`);
    }

    button.append(createIcon(item.icon), document.createTextNode(item.label));
    nav.append(button);
  }
  return nav;
}
