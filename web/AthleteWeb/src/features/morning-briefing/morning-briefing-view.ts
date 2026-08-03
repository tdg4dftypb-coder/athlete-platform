import { createCard, createSection } from "../../components/card";
import { createTextList } from "../../components/text-list";
import type { MorningBriefingPresentation } from "../../models/morning-briefing-presentation";

const navigationItems = ["Dzisiaj", "Trening", "Postępy", "Więcej"] as const;

export function renderMorningBriefing(model: MorningBriefingPresentation): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell";

  const main = document.createElement("main");
  main.className = "briefing";
  main.append(
    createHeader(model),
    createHero(model),
    createDecision(model),
    createListSection("Dlaczego właśnie taki plan?", "plan-reasons", model.reasons, "check"),
    createListSection("Co zmieniło się od wczoraj?", "daily-changes", model.changesSinceYesterday, "change"),
    createListSection("Plan na dziś", "today-plan", model.todayPlan, "plan"),
    createGoal(model),
    createShortcuts(model),
  );

  shell.append(main, createBottomNavigation());
  return shell;
}

function createHeader(model: MorningBriefingPresentation): HTMLElement {
  const header = document.createElement("header");
  header.className = "briefing-header reveal";

  const title = document.createElement("h1");
  const greeting = document.createElement("span");
  greeting.textContent = `${model.greeting},`;
  const athleteName = document.createElement("strong");
  athleteName.textContent = `${model.athleteName}.`;
  title.append(greeting, document.createTextNode(" "), athleteName);

  const context = document.createElement("p");
  context.className = "date-line";
  context.textContent = `${model.dateText} · ${model.timeText}`;

  header.append(title, context);
  return header;
}

function createHero(model: MorningBriefingPresentation): HTMLElement {
  const article = document.createElement("article");
  article.className = "hero-card reveal";
  article.setAttribute("aria-label", "Poranna odprawa");

  const message = document.createElement("div");
  message.className = "coach-message";
  for (const paragraph of model.coachMessage) {
    const text = document.createElement("p");
    text.textContent = paragraph;
    message.append(text);
  }

  article.append(message);
  return article;
}

function createDecision(model: MorningBriefingPresentation): HTMLElement {
  const section = createSection("Dzisiejsza decyzja", "today-decision");
  const card = createCard("decision-card");

  const title = document.createElement("p");
  title.className = "decision-title";
  title.textContent = model.decision.title;

  const details = document.createElement("p");
  details.className = "decision-details";
  details.textContent = `${model.decision.duration} • ${model.decision.intensity}`;

  card.append(title, details);
  section.append(card);
  return section;
}

function createListSection(
  title: string,
  id: string,
  items: readonly string[],
  variant: "check" | "change" | "plan",
): HTMLElement {
  const section = createSection(title, id);
  const card = createCard();
  card.append(createTextList(items, variant));
  section.append(card);
  return section;
}

function createGoal(model: MorningBriefingPresentation): HTMLElement {
  const section = createSection("Twój cel", "your-goal");
  const card = createCard("goal-card");

  const heading = document.createElement("div");
  heading.className = "goal-heading";
  const title = document.createElement("p");
  title.className = "goal-title";
  title.textContent = model.goal.title;
  const progressLabel = document.createElement("strong");
  progressLabel.textContent = model.goal.progressLabel;
  heading.append(title, progressLabel);

  const progress = document.createElement("div");
  progress.className = "progress-track";
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", "Postęp celu");
  progress.setAttribute("aria-valuemin", "0");
  progress.setAttribute("aria-valuemax", "100");
  progress.setAttribute("aria-valuenow", String(model.goal.progressValue * 100));
  progress.setAttribute("aria-valuetext", model.goal.progressLabel);
  const progressFill = document.createElement("span");
  progressFill.style.setProperty("--goal-progress", `${model.goal.progressValue * 100}%`);
  progress.append(progressFill);

  const timeline = document.createElement("p");
  timeline.className = "goal-timeline";
  timeline.textContent = model.goal.timeline;
  card.append(heading, progress, timeline);
  section.append(card);
  return section;
}

function createShortcuts(model: MorningBriefingPresentation): HTMLElement {
  const section = createSection("Skróty", "shortcuts");
  const list = document.createElement("ul");
  list.className = "shortcut-list";

  for (const shortcut of model.shortcuts) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = true;
    button.dataset.shortcut = shortcut.id;
    button.title = "Dostępne w kolejnych sprintach";
    const label = document.createElement("span");
    label.textContent = shortcut.label;
    const chevron = document.createElement("span");
    chevron.className = "shortcut-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.textContent = "›";
    button.append(label, chevron);
    item.append(button);
    list.append(item);
  }

  section.append(list);
  return section;
}

function createBottomNavigation(): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = "bottom-navigation";
  nav.setAttribute("aria-label", "Główna nawigacja");

  for (const label of navigationItems) {
    const button = document.createElement("button");
    const isActive = label === "Dzisiaj";
    button.type = "button";
    button.className = isActive ? "is-active" : "";
    button.disabled = !isActive;
    button.setAttribute("aria-current", isActive ? "page" : "false");
    if (!isActive) button.setAttribute("aria-label", `${label}, funkcja niedostępna`);

    const marker = document.createElement("span");
    marker.className = "nav-marker";
    marker.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.textContent = label;
    button.append(marker, text);
    nav.append(button);
  }

  return nav;
}
