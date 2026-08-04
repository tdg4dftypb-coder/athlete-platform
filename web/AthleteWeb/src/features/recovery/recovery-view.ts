import { createBottomNavigation } from "../../components/bottom-navigation";
import { createCard, createSection } from "../../components/card";
import { createIcon, type IconName } from "../../components/icon";
import { createPageHeader } from "../../components/page-header";
import { createStatusNotice } from "../../components/status-notice";
import type {
  RecoveryFactorPresentation,
  RecoveryPresentation,
  RecoveryPresentationHeader,
} from "../../models/recovery-presentation";
import type { RecoveryPresentationState } from "../../models/recovery-presentation-state";

export function renderRecoveryExperience(
  state: RecoveryPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell";
  shell.append(
    createStateContent(state, onBack, onRetry),
    createBottomNavigation({ currentView: "recovery" }),
  );

  return shell;
}

function createStateContent(
  state: RecoveryPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "recovery-experience";
  main.dataset.state = state.kind;

  switch (state.kind) {
    case "ready":
      appendAvailableRecovery(main, state.recovery, onBack);
      break;
    case "partial":
      main.append(createPageHeader(state.recovery.header, onBack));
      main.append(createStatusNotice({
        variant: "partial",
        title: "Niepełny obraz regeneracji",
        message: state.message,
        detailLabel: "Brakuje:",
        details: state.missingData,
      }));
      appendRecoveryBody(main, state.recovery);
      break;
    case "stale":
      main.append(createPageHeader(state.recovery.header, onBack));
      main.append(createStatusNotice({
        variant: "stale",
        title: "Ocena wymaga odświeżenia",
        message: state.message,
        details: [state.lastUpdatedText],
      }));
      appendRecoveryBody(main, state.recovery);
      break;
    case "unavailable":
      main.classList.add("recovery-experience--message");
      main.append(
        createPageHeader(state.header, onBack),
        createStatusNotice({
          variant: "unavailable",
          title: "Regeneracja jest niedostępna",
          message: state.message,
          details: [state.reason],
          nextAction: state.nextAction,
        }),
      );
      break;
    case "failure":
      main.classList.add("recovery-experience--message");
      main.append(
        createPageHeader(state.header, onBack),
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
      return createLoadingContent(state.message, onBack);
  }
  return main;
}

function appendAvailableRecovery(
  main: HTMLElement,
  model: RecoveryPresentation,
  onBack: () => void,
): void {
  main.append(createPageHeader(model.header, onBack));
  appendRecoveryBody(main, model);
}

function appendRecoveryBody(
  main: HTMLElement,
  model: RecoveryPresentation,
): void {
  main.append(
    createRecoveryHero(model),
    createFactors(model.factors),
    createInterpretation(model.interpretation),
  );
  if (model.trendSummary) main.append(createTrend(model.trendSummary));
  if (model.details.length > 0) main.append(createDetails(model));
}

function createRecoveryHero(model: RecoveryPresentation): HTMLElement {
  const article = document.createElement("article");
  article.className = `recovery-hero recovery-hero--${model.hero.tone} reveal`;
  article.setAttribute("aria-labelledby", "recovery-status");

  const copy = document.createElement("div");
  copy.className = "recovery-hero__copy";
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Dzisiejsza regeneracja";
  const title = document.createElement("h2");
  title.id = "recovery-status";
  title.textContent = model.hero.statusLabel;
  const narrative = document.createElement("p");
  narrative.className = "recovery-hero__narrative";
  narrative.textContent = model.hero.narrative;
  copy.append(eyebrow, title, narrative);

  const mark = document.createElement("div");
  mark.className = "recovery-hero__mark";
  mark.setAttribute("aria-hidden", "true");
  mark.append(createIcon("heart"));

  article.append(copy, mark);
  if (model.hero.score !== null) {
    const score = document.createElement("div");
    score.className = "recovery-score";
    score.setAttribute("aria-label", `${model.hero.scoreLabel ?? "Recovery Score"}: ${model.hero.score} na 100`);
    const value = document.createElement("strong");
    value.textContent = String(model.hero.score);
    const scale = document.createElement("span");
    scale.textContent = "/100";
    const label = document.createElement("small");
    label.textContent = model.hero.scoreLabel ?? "Recovery Score";
    score.append(value, scale, label);
    article.append(score);
  }
  return article;
}

function createFactors(items: readonly RecoveryFactorPresentation[]): HTMLElement {
  const section = createSection("Najważniejsze czynniki", "recovery-factors");
  section.classList.add("recovery-factors");
  const list = document.createElement("ul");
  list.className = "recovery-factor-list";
  for (const factor of items) list.append(createFactor(factor));
  section.append(list);
  return section;
}

function createFactor(model: RecoveryFactorPresentation): HTMLLIElement {
  const icons: Readonly<Record<RecoveryFactorPresentation["id"], IconName>> = {
    hrv: "heart",
    sleep: "moon",
    "resting-heart-rate": "gauge",
    fatigue: "trend-down",
  };
  const item = document.createElement("li");
  item.className = `recovery-factor recovery-factor--${model.tone}`;

  const icon = document.createElement("span");
  icon.className = "recovery-factor__icon";
  icon.setAttribute("aria-hidden", "true");
  icon.append(createIcon(icons[model.id]));

  const copy = document.createElement("div");
  copy.className = "recovery-factor__copy";
  const heading = document.createElement("div");
  heading.className = "recovery-factor__heading";
  const label = document.createElement("h3");
  label.textContent = model.label;
  const status = document.createElement("span");
  status.className = "factor-status";
  status.textContent = model.statusLabel;
  heading.append(label, status);

  const value = document.createElement("p");
  value.className = "recovery-factor__value";
  value.textContent = model.valueText ?? "Wartość niedostępna";
  const description = document.createElement("p");
  description.className = "recovery-factor__description";
  description.textContent = model.description;
  copy.append(heading, value);
  if (model.contextText) {
    const context = document.createElement("p");
    context.className = "recovery-factor__context";
    context.textContent = model.contextText;
    copy.append(context);
  }
  copy.append(description);
  if (model.trendText) {
    const trend = document.createElement("p");
    trend.className = "trend-indicator";
    trend.append(createIcon("trend-up"), document.createTextNode(model.trendText));
    copy.append(trend);
  }
  item.append(icon, copy);
  return item;
}

function createInterpretation(text: string): HTMLElement {
  const section = createSection("Co to oznacza na dziś?", "recovery-meaning");
  section.classList.add("explanation-section");
  const card = createCard("explanation-card");
  const icon = document.createElement("span");
  icon.className = "explanation-card__icon";
  icon.setAttribute("aria-hidden", "true");
  icon.append(createIcon("coach"));
  const message = document.createElement("p");
  message.textContent = text;
  card.append(icon, message);
  section.append(card);
  return section;
}

function createTrend(text: string): HTMLElement {
  const section = createSection("Krótki trend", "recovery-trend");
  section.classList.add("recovery-trend-section");
  const card = createCard("trend-card");
  card.append(createIcon("trend-up"));
  const copy = document.createElement("p");
  copy.textContent = text;
  card.append(copy);
  section.append(card);
  return section;
}

function createDetails(model: RecoveryPresentation): HTMLElement {
  const section = createSection("Dane szczegółowe", "recovery-details");
  section.classList.add("recovery-details");
  const list = document.createElement("dl");
  list.className = "recovery-detail-list card";
  for (const detail of model.details) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = detail.label;
    const value = document.createElement("dd");
    const metric = document.createElement("strong");
    metric.textContent = detail.valueText;
    const description = document.createElement("small");
    description.textContent = detail.description;
    value.append(metric, description);
    item.append(term, value);
    list.append(item);
  }
  section.append(list);
  return section;
}

function createLoadingContent(
  message: string,
  onBack: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "recovery-experience recovery-experience--loading";
  main.dataset.state = "loading";
  main.setAttribute("aria-busy", "true");
  const header: RecoveryPresentationHeader = {
    title: "Regeneracja",
    dateText: "Ładowanie danych",
    lastUpdatedText: "Aktualizacja w toku",
    freshnessLabel: null,
  };
  const status = document.createElement("p");
  status.className = "loading-label";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = message;
  const skeleton = document.createElement("div");
  skeleton.className = "skeleton-layout";
  skeleton.setAttribute("aria-hidden", "true");
  for (const variant of ["recovery-hero", "recovery-factor", "recovery-factor", "card"]) {
    const block = document.createElement("div");
    block.className = `skeleton-block skeleton-block--${variant}`;
    skeleton.append(block);
  }
  main.append(createPageHeader(header, onBack), status, skeleton);
  return main;
}
