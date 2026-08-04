import { createBottomNavigation } from "../../components/bottom-navigation";
import { createCard, createSection } from "../../components/card";
import { createIcon } from "../../components/icon";
import { createPageHeader } from "../../components/page-header";
import { createStatusNotice } from "../../components/status-notice";
import type {
  MealTimelineItem,
  NutritionFocusItem,
  NutritionHeroPresentation,
  NutritionHydrationPresentation,
  NutritionPresentation,
  NutritionTechnicalPresentation,
} from "../../models/nutrition-presentation";
import type { NutritionPresentationState } from "../../models/nutrition-presentation-state";

export function renderNutritionExperience(
  state: NutritionPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell nutrition-shell";
  shell.append(
    createStateContent(state, onBack, onRetry),
    createBottomNavigation(),
  );
  return shell;
}

function createStateContent(
  state: NutritionPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing nutrition-view";

  switch (state.kind) {
    case "ready":
      appendAvailableNutrition(main, state.nutrition, onBack);
      break;
    case "partial":
      main.append(createPageHeader(state.nutrition.header, onBack));
      main.append(
        createStatusNotice({
          variant: "partial",
          title: "Częściowe dane żywieniowe",
          message: state.message,
          detailLabel: "Brakuje:",
          details: state.missingData,
        }),
      );
      appendNutritionBody(main, state.nutrition);
      break;
    case "stale":
      main.append(createPageHeader(state.nutrition.header, onBack));
      main.append(
        createStatusNotice({
          variant: "stale",
          title: "Dane wymagają odświeżenia",
          message: state.message,
          details: [state.lastUpdatedText],
        }),
      );
      appendNutritionBody(main, state.nutrition);
      break;
    case "unavailable":
      main.classList.add("briefing--message");
      main.append(
        createPageHeader(state.header, onBack),
        createStatusNotice({
          variant: "unavailable",
          title: "Plan żywieniowy jest niedostępny",
          message: state.message,
          details: [state.reason],
          nextAction: state.nextAction,
        }),
      );
      break;
    case "failure":
      main.classList.add("briefing--message");
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

function appendAvailableNutrition(
  main: HTMLElement,
  model: NutritionPresentation,
  onBack: () => void,
): void {
  main.append(createPageHeader(model.header, onBack));
  appendNutritionBody(main, model);
}

function appendNutritionBody(
  main: HTMLElement,
  model: NutritionPresentation,
): void {
  main.append(
    createHeroCard(model.hero),
    createFocusSection(model.focusItems),
    createMealTimelineSection(model.mealTimeline),
    createHydrationSection(model.hydration),
    createCoachSummarySection(model.coachSummary),
    createTechnicalSection(model.technical),
  );
}

function createLoadingContent(message: string, onBack: () => void): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing briefing--loading nutrition-view";
  main.setAttribute("aria-busy", "true");

  const header = createPageHeader(
    {
      title: "Odżywianie",
      dateText: "Wczytywanie...",
      lastUpdatedText: "Pobieranie strategii żywieniowej...",
      freshnessLabel: null,
    },
    onBack,
  );

  const status = document.createElement("p");
  status.className = "loading-label";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = message;

  const skeleton = document.createElement("div");
  skeleton.className = "skeleton-layout";
  skeleton.setAttribute("aria-hidden", "true");
  for (const variant of ["header", "hero", "card", "card"] as const) {
    const block = document.createElement("div");
    block.className = `skeleton-block skeleton-block--${variant}`;
    skeleton.append(block);
  }

  main.append(header, status, skeleton);
  return main;
}

function createHeroCard(hero: NutritionHeroPresentation): HTMLElement {
  const card = document.createElement("article");
  card.className = "hero-card nutrition-hero-card reveal";
  card.setAttribute("aria-label", "Podsumowanie strategii żywieniowej");

  const copy = document.createElement("div");
  copy.className = "nutrition-hero__copy";

  const badge = document.createElement("div");
  badge.className = `nutrition-hero__badge nutrition-hero__badge--${hero.statusVariant}`;
  badge.append(createIcon("nutrition"));
  const badgeText = document.createElement("span");
  badgeText.textContent = hero.statusBadgeText;
  badge.append(badgeText);

  const headline = document.createElement("h2");
  headline.className = "nutrition-hero__headline";
  headline.textContent = hero.headline;

  const sub = document.createElement("p");
  sub.className = "nutrition-hero__subheading";
  sub.textContent = hero.subheading;

  const timeframe = document.createElement("p");
  timeframe.className = "nutrition-hero__timeframe";
  timeframe.textContent = hero.timeframeText;

  copy.append(badge, headline, sub, timeframe);
  card.append(copy);
  return card;
}

function createFocusSection(
  items: readonly NutritionFocusItem[],
): HTMLElement {
  const section = createSection("Dzisiejszy akcent żywieniowy", "nutrition-focus");
  section.classList.add("nutrition-focus-section");

  const list = document.createElement("ul");
  list.className = "focus-grid";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "focus-card-item";

    const card = createCard(`focus-card focus-card--${item.status}`);

    const header = document.createElement("div");
    header.className = "focus-card__header";

    const titleBox = document.createElement("div");
    titleBox.className = "focus-card__title-box";

    const statusIcon = document.createElement("span");
    statusIcon.className = `focus-card__status-icon focus-card__status-icon--${item.status}`;
    statusIcon.append(createIcon(item.status === "alert" ? "trend-down" : "check"));

    const title = document.createElement("h3");
    title.className = "focus-card__title";
    title.textContent = item.title;

    titleBox.append(statusIcon, title);

    const highlight = document.createElement("span");
    highlight.className = "focus-card__highlight";
    highlight.textContent = item.highlightText;

    header.append(titleBox, highlight);

    const desc = document.createElement("p");
    desc.className = "focus-card__description";
    desc.textContent = item.description;

    card.append(header, desc);
    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createMealTimelineSection(
  meals: readonly MealTimelineItem[],
): HTMLElement {
  const section = createSection("Harmonogram posiłków", "meal-timeline");
  section.classList.add("meal-timeline-section");

  const list = document.createElement("ol");
  list.className = "timeline-list";

  for (const meal of meals) {
    const li = document.createElement("li");
    li.className = "timeline-item";

    const card = createCard(`meal-card meal-card--${meal.timingLabel.toLowerCase().replace(/\s+/g, "-")}`);

    const timeBadge = document.createElement("span");
    timeBadge.className = "meal-card__time";
    timeBadge.textContent = meal.timeText;

    const content = document.createElement("div");
    content.className = "meal-card__content";

    const header = document.createElement("div");
    header.className = "meal-card__header";

    const title = document.createElement("h3");
    title.className = "meal-card__name";
    title.textContent = meal.mealName;

    const tag = document.createElement("span");
    tag.className = "meal-card__tag";
    tag.textContent = meal.timingLabel;

    header.append(title, tag);

    const desc = document.createElement("p");
    desc.className = "meal-card__desc";
    desc.textContent = meal.description;

    const targets = document.createElement("div");
    targets.className = "meal-card__targets";
    const carbs = document.createElement("span");
    carbs.className = "meal-target-pill meal-target-pill--carbs";
    carbs.textContent = meal.targetCarbs;
    const protein = document.createElement("span");
    protein.className = "meal-target-pill meal-target-pill--protein";
    protein.textContent = meal.targetProtein;
    targets.append(carbs, protein);

    content.append(header, desc, targets);
    card.append(timeBadge, content);
    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createHydrationSection(
  hydration: NutritionHydrationPresentation,
): HTMLElement {
  const section = createSection(hydration.title, "hydration");
  section.classList.add("hydration-section");

  const card = createCard("hydration-card");

  const header = document.createElement("div");
  header.className = "hydration-card__header";

  const volume = document.createElement("div");
  volume.className = "hydration-card__volume";
  const current = document.createElement("strong");
  current.textContent = `${(hydration.currentVolumeMl / 1000).toFixed(1)}L`;
  const target = document.createElement("span");
  target.textContent = ` / ${(hydration.targetVolumeMl / 1000).toFixed(1)}L`;
  volume.append(current, target);

  const pctLabel = document.createElement("span");
  pctLabel.className = "hydration-card__pct";
  pctLabel.textContent = hydration.progressLabel;

  header.append(volume, pctLabel);

  const pct = Math.min(100, Math.round((hydration.currentVolumeMl / hydration.targetVolumeMl) * 100));
  const track = document.createElement("div");
  track.className = "hydration-track";
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-label", "Poziom nawodnienia");
  track.setAttribute("aria-valuenow", String(pct));
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");

  const fill = document.createElement("span");
  fill.className = "hydration-fill";
  fill.style.width = `${pct}%`;
  track.append(fill);

  const status = document.createElement("p");
  status.className = "hydration-card__status";
  status.textContent = hydration.statusText;

  card.append(header, track, status);
  section.append(card);
  return section;
}

function createCoachSummarySection(
  summary: NutritionPresentation["coachSummary"],
): HTMLElement {
  const section = createSection(summary.title, "ai-summary");
  section.classList.add("ai-summary-section");

  const card = createCard("ai-summary-card");
  const icon = document.createElement("span");
  icon.className = "ai-summary__icon";
  icon.setAttribute("aria-hidden", "true");
  icon.append(createIcon("coach"));

  const copy = document.createElement("div");
  copy.className = "ai-summary__copy";

  for (const paragraph of summary.paragraphs) {
    const p = document.createElement("p");
    p.textContent = paragraph;
    copy.append(p);
  }

  card.append(icon, copy);
  section.append(card);
  return section;
}

function createTechnicalSection(
  tech: NutritionTechnicalPresentation,
): HTMLElement {
  const section = createSection(tech.title, "technical-nutrition");
  section.classList.add("technical-metrics-section");

  const card = createCard("technical-metrics-card");
  const dl = document.createElement("dl");
  dl.className = "technical-grid";

  for (const metric of tech.metrics) {
    const row = document.createElement("div");
    row.className = "technical-row";

    const dt = document.createElement("dt");
    const label = document.createElement("span");
    label.textContent = metric.label;
    dt.append(label);

    if (metric.description) {
      const desc = document.createElement("small");
      desc.textContent = metric.description;
      dt.append(desc);
    }

    const dd = document.createElement("dd");
    const val = document.createElement("strong");
    val.textContent = metric.valueText;
    dd.append(val);

    if (metric.targetText) {
      const target = document.createElement("span");
      target.className = "metric-change-badge";
      target.textContent = metric.targetText;
      dd.append(target);
    }

    row.append(dt, dd);
    dl.append(row);
  }

  card.append(dl);
  section.append(card);
  return section;
}
