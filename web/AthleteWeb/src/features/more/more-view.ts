import { createBottomNavigation } from "../../components/bottom-navigation";
import { createSection } from "../../components/card";
import { createIcon, type IconName } from "../../components/icon";
import { createPageHeader } from "../../components/page-header";

export function renderMoreExperience(
  onBack: () => void = () => undefined,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell more-shell";

  const main = document.createElement("main");
  main.className = "briefing more-view";

  const header = createPageHeader(
    {
      title: "Więcej",
      dateText: "Moduły i obszary analityczne",
      lastUpdatedText: "Wybierz strefę szczegółową",
      freshnessLabel: null,
    },
    onBack,
  );

  const section = createSection("Dostępne strefy", "more-sections");
  section.classList.add("more-section");

  const list = document.createElement("ul");
  list.className = "more-grid";
  list.style.cssText = "display: flex; flex-direction: column; gap: 0.75rem; list-style: none; padding: 0; margin: 0;";

  const items: readonly {
    title: string;
    description: string;
    icon: IconName;
    view: "recovery" | "nutrition" | "body" | "biomarkers" | "icons";
  }[] = [
    {
      title: "Wyniki badań (Biomarkers)",
      description: "Przegląd badań laboratoryjnych, wskaźniki i weryfikacja danych.",
      icon: "target",
      view: "biomarkers",
    },
    {
      title: "Regeneracja (Recovery)",
      description: "Szczegółowa ocena jakości snu, HRV i gotowości do wysiłku.",
      icon: "heart",
      view: "recovery",
    },
    {
      title: "Odżywianie (Nutrition)",
      description: "Strategia żywieniowa okołotreningowa, bilans i nawodnienie.",
      icon: "sun",
      view: "nutrition",
    },
    {
      title: "Skład ciała (Body Composition)",
      description: "Trendy masy ciała, obwód talii i tkanka tłuszczowa.",
      icon: "target",
      view: "body",
    },
    {
      title: "System ikon aktywności",
      description: "Lokalna biblioteka wektorowych ikon dyscyplin sportowych.",
      icon: "activity-cycling",
      view: "icons",
    },
  ];

  for (const item of items) {
    const li = document.createElement("li");
    li.style.listStyle = "none";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "card more-card";
    button.style.cssText =
      "display: grid; grid-template-columns: 2.8rem minmax(0, 1fr) 1.2rem; gap: 0.85rem; align-items: center; width: 100%; text-align: left; cursor: pointer; padding: 0.95rem 1.05rem;";
    button.setAttribute("aria-label", `Otwórz: ${item.title}`);

    button.addEventListener("click", () => {
      const url = new URL(window.location.href);
      url.searchParams.set("view", item.view);
      window.history.pushState({ athleteView: item.view }, "", url);
      window.dispatchEvent(new Event("popstate"));
    });

    const iconBadge = document.createElement("span");
    iconBadge.className = "icon-badge icon-badge--recovery";
    iconBadge.setAttribute("aria-hidden", "true");
    iconBadge.append(createIcon(item.icon));

    const content = document.createElement("div");
    const title = document.createElement("h2");
    title.style.cssText = "font-size: 0.95rem; font-weight: 680; margin: 0 0 0.2rem 0; color: var(--color-text-primary);";
    title.textContent = item.title;

    const desc = document.createElement("p");
    desc.style.cssText = "font-size: 0.82rem; margin: 0; color: var(--color-text-secondary); line-height: 1.4;";
    desc.textContent = item.description;

    content.append(title, desc);

    button.append(iconBadge, content, createIcon("chevron"));
    li.append(button);
    list.append(li);
  }

  section.append(list);
  main.append(header, section);

  shell.append(main, createBottomNavigation({ currentView: "more" }));
  return shell;
}
