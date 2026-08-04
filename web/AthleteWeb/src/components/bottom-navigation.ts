import { createIcon, type IconName } from "./icon";

const navigationItems: readonly { label: string; icon: IconName }[] = [
  { label: "Dzisiaj", icon: "sun" },
  { label: "Trening", icon: "runner" },
  { label: "Postępy", icon: "chart" },
  { label: "Więcej", icon: "more" },
];

export function createBottomNavigation(): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = "bottom-navigation";
  nav.setAttribute("aria-label", "Główna nawigacja");
  for (const item of navigationItems) {
    const button = document.createElement("button");
    const isActive = item.label === "Dzisiaj";
    button.type = "button";
    button.className = isActive ? "is-active" : "";
    button.disabled = !isActive;
    button.setAttribute("aria-current", isActive ? "page" : "false");
    if (!isActive) {
      button.setAttribute("aria-label", `${item.label}, funkcja niedostępna`);
    }
    button.append(createIcon(item.icon), document.createTextNode(item.label));
    nav.append(button);
  }
  return nav;
}
