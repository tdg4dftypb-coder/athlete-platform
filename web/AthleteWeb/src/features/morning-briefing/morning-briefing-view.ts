import { createCard, createSection } from "../../components/card";
import { createIcon, type IconName } from "../../components/icon";
import { createStatusNotice } from "../../components/status-notice";
import type {
  MorningBriefingHeader,
  MorningBriefingPresentation,
  MorningBriefingShortcut,
} from "../../models/morning-briefing-presentation";
import type { MorningBriefingPresentationState } from "../../models/morning-briefing-presentation-state";

const navigationItems: readonly { label: string; icon: IconName }[] = [
  { label: "Dzisiaj", icon: "sun" },
  { label: "Trening", icon: "runner" },
  { label: "Postępy", icon: "chart" },
  { label: "Więcej", icon: "more" },
];

const semanticIcons: readonly IconName[] = ["heart", "moon", "gauge"];

export function renderMorningBriefing(
  state: MorningBriefingPresentationState,
  onRetry: () => void,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell";
  shell.append(createStateContent(state, onRetry), createBottomNavigation());
  return shell;
}

function createStateContent(
  state: MorningBriefingPresentationState,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing";

  switch (state.kind) {
    case "ready":
      appendAvailableBriefing(main, state.briefing);
      break;
    case "partial":
      main.append(createHeader(state.briefing));
      main.append(createStatusNotice({
        variant: "partial",
        title: "Niepełne dane",
        message: state.message,
        detailLabel: "Brakuje:",
        details: state.missingData,
      }));
      appendBriefingBody(main, state.briefing);
      break;
    case "stale":
      main.append(createHeader(state.briefing));
      main.append(createStatusNotice({
        variant: "stale",
        title: "Dane wymagają odświeżenia",
        message: state.message,
        details: [state.lastUpdatedText],
      }));
      appendBriefingBody(main, state.briefing);
      break;
    case "unavailable":
      main.classList.add("briefing--message");
      main.append(
        createHeader(state.header),
        createStatusNotice({
          variant: "unavailable",
          title: "Briefing jest dziś niedostępny",
          message: state.message,
          details: [state.reason],
          nextAction: state.nextAction,
        }),
      );
      break;
    case "failure":
      main.classList.add("briefing--message");
      main.append(
        createHeader(state.header),
        createStatusNotice({
          variant: "failure",
          title: "Nie udało się odświeżyć",
          message: state.message,
          details: [state.supportingText],
          retryLabel: state.retryLabel,
          onRetry,
        }),
      );
      break;
    case "loading":
      return createLoadingContent(state.message);
  }
  return main;
}

function appendAvailableBriefing(main: HTMLElement, model: MorningBriefingPresentation): void {
  main.append(createHeader(model));
  appendBriefingBody(main, model);
}

function appendBriefingBody(main: HTMLElement, model: MorningBriefingPresentation): void {
  main.append(createHero(model), createDecisionExperience(model), createGoal(model), createShortcuts(model));
}

function createHeader(model: MorningBriefingHeader): HTMLElement {
  const header = document.createElement("header");
  header.className = "briefing-header reveal";

  const avatar = document.createElement("span");
  avatar.className = "profile-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = model.athleteName.slice(0, 1);

  const copy = document.createElement("div");
  copy.className = "header-copy";
  const title = document.createElement("h1");
  title.tabIndex = -1;
  title.textContent = `${model.greeting}, ${model.athleteName}!`;
  const context = document.createElement("p");
  context.className = "date-line";
  context.textContent = model.dateText;
  copy.append(title, context);

  const coach = document.createElement("div");
  coach.className = "coach-badge";
  coach.append(createIcon("coach"));
  const coachCopy = document.createElement("span");
  coachCopy.innerHTML = "<strong>AI Coach</strong><small>Twój trener</small>";
  coach.append(coachCopy);

  header.append(avatar, copy, coach);
  return header;
}

function createLoadingContent(message: string): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing briefing--loading";
  main.setAttribute("aria-busy", "true");
  const status = document.createElement("p");
  status.className = "loading-label";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = message;
  const skeleton = document.createElement("div");
  skeleton.className = "skeleton-layout";
  skeleton.setAttribute("aria-hidden", "true");
  for (const variant of ["header", "hero", "card", "card", "shortcuts"] as const) {
    const block = document.createElement("div");
    block.className = `skeleton-block skeleton-block--${variant}`;
    skeleton.append(block);
  }
  main.append(status, skeleton);
  return main;
}

function createHero(model: MorningBriefingPresentation): HTMLElement {
  const article = document.createElement("article");
  article.className = "hero-card reveal";
  article.setAttribute("aria-label", "Poranna odprawa");
  const art = document.createElement("span");
  art.className = "hero-art";
  art.setAttribute("aria-hidden", "true");
  const message = document.createElement("div");
  message.className = "coach-message";
  model.coachMessage.forEach((paragraph, index) => {
    const text = document.createElement(index === 0 ? "h2" : "p");
    if (index === model.coachMessage.length - 1) text.className = "hero-emphasis";
    text.textContent = paragraph;
    message.append(text);
  });
  const button = document.createElement("button");
  button.className = "listen-button";
  button.type = "button";
  button.disabled = true;
  button.title = "Audio będzie dostępne w przyszłości";
  button.append(createIcon("play"), document.createTextNode("Posłuchaj podsumowania (30 s)"));
  message.append(button);
  article.append(art, message);
  return article;
}

function createDecisionExperience(model: MorningBriefingPresentation): HTMLElement {
  const section = document.createElement("section");
  section.className = "decision-experience reveal";
  section.setAttribute("aria-labelledby", "today-decision");
  section.append(createDecision(model), createReasons(model.reasons));
  if (model.changesSinceYesterday.length > 0) section.append(createChanges(model.changesSinceYesterday));
  section.append(createTodayPlan(model.todayPlan));
  return section;
}

function createDecision(model: MorningBriefingPresentation): HTMLElement {
  const header = document.createElement("div");
  header.className = "decision-summary";
  const icon = createIconBadge("runner", "training");
  const copy = document.createElement("div");
  const eyebrow = document.createElement("h2");
  eyebrow.id = "today-decision";
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Dzisiejsza decyzja";
  const title = document.createElement("p");
  title.className = "decision-title";
  title.textContent = model.decision.title;
  const details = document.createElement("p");
  details.className = "decision-details";
  details.textContent = `${model.decision.duration.replace("minut", "min")} • ${model.decision.intensity}`;
  copy.append(eyebrow, title, details);
  header.append(icon, copy, createIcon("chevron"));
  return header;
}

function createReasons(items: readonly string[]): HTMLElement {
  const region = document.createElement("div");
  region.className = "reason-region";
  const heading = document.createElement("div");
  heading.className = "section-heading";
  const title = document.createElement("h2");
  title.id = "plan-reasons";
  title.textContent = "Dlaczego właśnie taki plan?";
  const details = document.createElement("button");
  details.type = "button";
  details.disabled = true;
  details.textContent = "Pokaż szczegóły";
  details.append(createIcon("chevron"));
  heading.append(title, details);
  const list = document.createElement("ul");
  list.className = "reason-grid";
  items.forEach((item, index) => {
    const metadata = getReasonMetadata(item);
    const entry = document.createElement("li");
    entry.className = `semantic-item semantic-item--${index % 3}`;
    entry.append(createIconBadge(semanticIcons[index % 3]!, `semantic-${index % 3}`));
    const copy = document.createElement("div");
    const label = document.createElement("strong");
    label.textContent = metadata.label;
    const text = document.createElement("p");
    text.textContent = item;
    const value = document.createElement("small");
    value.textContent = metadata.support ?? "";
    copy.append(label, text);
    if (metadata.support) copy.append(value);
    entry.append(copy);
    list.append(entry);
  });
  const note = document.createElement("p");
  note.className = "recovery-note";
  note.append(createIcon("lock"), document.createTextNode("Szczegółowe dane dostępne w sekcji Regeneracja"));
  region.append(heading, list, note);
  return region;
}

function getReasonMetadata(item: string): { label: string; support: string | null } {
  const previewMetadata: Readonly<Record<string, { label: string; support: string }>> = {
    "HRV wróciło do normy": { label: "HRV", support: "Lepsze o 7% vs wczoraj" },
    "Sen był lepszy niż zwykle": { label: "Sen", support: "7h 32m vs 6h 15m" },
    "Zmęczenie spadło": { label: "Zmęczenie", support: "Spadek o 18%" },
  };
  const preview = previewMetadata[item];
  if (preview) return preview;
  if (/HRV/i.test(item)) return { label: "HRV", support: null };
  if (/sen|snu/i.test(item)) return { label: "Sen", support: null };
  if (/zmęcz|obciąż/i.test(item)) return { label: "Zmęczenie", support: null };
  return { label: "Uzasadnienie", support: null };
}

function createChanges(items: readonly string[]): HTMLElement {
  const card = document.createElement("section");
  card.className = "changes-card";
  card.setAttribute("aria-labelledby", "daily-changes");
  const title = document.createElement("h2");
  title.id = "daily-changes";
  title.append(createIcon("trend-up"), document.createTextNode("Co zmieniło się od wczoraj?"));
  const list = document.createElement("ul");
  list.className = "changes-grid";
  const labels = ["HRV", "Sen", "Zmęczenie"];
  const current = ["+7%", "Lepszy", "Mniejsze"];
  const previous = ["42 ms → 45 ms", "7h 32m vs 6h 15m", "312 → 256"];
  items.forEach((_item, index) => {
    const entry = document.createElement("li");
    entry.append(createIconBadge(index === 2 ? "trend-down" : index === 1 ? "check" : "trend-up", "change"));
    const copy = document.createElement("div");
    const label = document.createElement("span");
    label.textContent = labels[index] ?? "Zmiana";
    const value = document.createElement("strong");
    value.textContent = current[index] ?? "Lepszy";
    const before = document.createElement("small");
    before.textContent = previous[index] ?? "Względem wczoraj";
    copy.append(label, value, before);
    entry.append(copy);
    list.append(entry);
  });
  card.append(title, list);
  return card;
}

function createTodayPlan(items: readonly string[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "today-plan";
  section.setAttribute("aria-labelledby", "today-plan");
  const title = document.createElement("h2");
  title.id = "today-plan";
  title.textContent = "Plan na dziś";
  const list = document.createElement("ul");
  list.className = "plan-list";
  const icons: readonly IconName[] = ["runner", "nutrition", "moon"];
  const supports = ["Jakość ponad objętość.", "Przed treningiem (ok. 60–90 min).", "Regeneracja to Twój priorytet."];
  items.forEach((item, index) => {
    const entry = document.createElement("li");
    entry.className = `plan-item plan-item--${index % 3}`;
    entry.append(createIconBadge(icons[index % 3]!, `plan-${index % 3}`));
    const copy = document.createElement("div");
    const label = document.createElement("strong");
    label.textContent = item;
    const support = document.createElement("small");
    support.textContent = supports[index] ?? "Szczegóły planu";
    copy.append(label, support);
    entry.append(copy, createIcon("chevron"));
    list.append(entry);
  });
  section.append(title, list);
  return section;
}

function createGoal(model: MorningBriefingPresentation): HTMLElement {
  const section = createSection("Twój cel", "your-goal");
  section.classList.add("goal-section");
  const card = createCard("goal-card");
  const icon = createIconBadge("target", "recovery");
  const copy = document.createElement("div");
  copy.className = "goal-copy";
  const title = document.createElement("p");
  title.className = "goal-title";
  title.textContent = model.goal.title;
  const support = document.createElement("p");
  support.className = "goal-support";
  support.textContent = "Stopniowo zwiększamy Twoją formę.";
  copy.append(title, support);
  const timeline = document.createElement("p");
  timeline.className = "goal-timeline";
  timeline.textContent = model.goal.timeline;
  const progressLabel = document.createElement("strong");
  progressLabel.className = "goal-value";
  progressLabel.textContent = model.goal.progressLabel;
  const progress = document.createElement("div");
  progress.className = "progress-track";
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", model.goal.progressAccessibilityLabel);
  progress.setAttribute("aria-valuemin", "0");
  progress.setAttribute("aria-valuemax", "100");
  progress.setAttribute("aria-valuetext", model.goal.progressLabel);
  if (model.goal.progressValue !== null) progress.setAttribute("aria-valuenow", String(model.goal.progressValue * 100));
  const fill = document.createElement("span");
  fill.style.setProperty("--goal-progress", model.goal.progressValue === null ? "0%" : `${model.goal.progressValue * 100}%`);
  progress.append(fill);
  card.append(icon, copy, timeline, progressLabel, progress);
  section.append(card);
  return section;
}

function createShortcuts(model: MorningBriefingPresentation): HTMLElement {
  const section = createSection("Dowiedz się więcej", "shortcuts");
  section.classList.add("shortcut-section");
  const list = document.createElement("ul");
  list.className = "shortcut-grid";
  const metadata: Readonly<Record<string, { icon: IconName; description: string }>> = {
    recovery: { icon: "heart", description: "Jak się regenerujesz" },
    training: { icon: "runner", description: "Szczegóły planu" },
    nutrition: { icon: "apple", description: "Wsparcie żywieniowe" },
    history: { icon: "history", description: "Co wydarzyło się wcześniej" },
  };
  for (const shortcut of model.shortcuts) list.append(createShortcut(shortcut, metadata[shortcut.id]));
  section.append(list);
  return section;
}

function createShortcut(shortcut: MorningBriefingShortcut, meta?: { icon: IconName; description: string }): HTMLLIElement {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.disabled = true;
  button.dataset.shortcut = shortcut.id;
  button.title = "Dostępne w kolejnych sprintach";
  button.append(createIcon(meta?.icon ?? "more"));
  const label = document.createElement("strong");
  label.textContent = shortcut.label;
  const description = document.createElement("small");
  description.textContent = meta?.description ?? "Więcej informacji";
  button.append(label, description, createIcon("chevron"));
  item.append(button);
  return item;
}

function createBottomNavigation(): HTMLElement {
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
    if (!isActive) button.setAttribute("aria-label", `${item.label}, funkcja niedostępna`);
    button.append(createIcon(item.icon), document.createTextNode(item.label));
    nav.append(button);
  }
  return nav;
}

function createIconBadge(icon: IconName, variant: string): HTMLSpanElement {
  const badge = document.createElement("span");
  badge.className = `icon-badge icon-badge--${variant}`;
  badge.setAttribute("aria-hidden", "true");
  badge.append(createIcon(icon));
  return badge;
}
