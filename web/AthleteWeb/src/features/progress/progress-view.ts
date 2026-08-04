import { createBottomNavigation } from "../../components/bottom-navigation";
import { createCard, createSection } from "../../components/card";
import { createIcon } from "../../components/icon";
import { createPageHeader } from "../../components/page-header";

import { createStatusNotice } from "../../components/status-notice";
import type {
  ProgressAreaToImproveItem,
  ProgressHeroPresentation,
  ProgressImprovementItem,
  ProgressPresentation,
  ProgressTechnicalMetricsPresentation,
  ProgressTrendPresentation,
} from "../../models/progress-presentation";
import type { ProgressPresentationState } from "../../models/progress-presentation-state";

export function renderProgressExperience(
  state: ProgressPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell progress-shell";
  shell.append(
    createStateContent(state, onBack, onRetry),
    createBottomNavigation(),
  );
  return shell;
}

function createStateContent(
  state: ProgressPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing progress-view";

  switch (state.kind) {
    case "ready":
      appendAvailableProgress(main, state.progress, onBack);
      break;
    case "partial":
      main.append(createPageHeader(state.progress.header, onBack));
      main.append(
        createStatusNotice({
          variant: "partial",
          title: "Częściowe dane o postępach",
          message: state.message,
          detailLabel: "Brakuje:",
          details: state.missingData,
        }),
      );
      appendProgressBody(main, state.progress);
      break;
    case "stale":
      main.append(createPageHeader(state.progress.header, onBack));
      main.append(
        createStatusNotice({
          variant: "stale",
          title: "Dane wymagają odświeżenia",
          message: state.message,
          details: [state.lastUpdatedText],
        }),
      );
      appendProgressBody(main, state.progress);
      break;
    case "unavailable":
      main.classList.add("briefing--message");
      main.append(
        createPageHeader(state.header, onBack),
        createStatusNotice({
          variant: "unavailable",
          title: "Analiza postępów jest niedostępna",
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

function appendAvailableProgress(
  main: HTMLElement,
  model: ProgressPresentation,
  onBack: () => void,
): void {
  main.append(createPageHeader(model.header, onBack));
  appendProgressBody(main, model);
}

function appendProgressBody(
  main: HTMLElement,
  model: ProgressPresentation,
): void {
  main.append(
    createHeroCard(model.hero),
    createImprovementsSection(model.improvements),
    createAreasToImproveSection(model.areasToImprove),
    createTrendSection(model.trend),
    createAISummarySection(model.aiSummary),
    createTechnicalMetricsSection(model.technicalMetrics),
  );
}

function createLoadingContent(message: string, onBack: () => void): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing briefing--loading progress-view";
  main.setAttribute("aria-busy", "true");

  const header = createPageHeader(
    {
      title: "Postępy",
      dateText: "Wczytywanie...",
      lastUpdatedText: "Analizowanie historii obciążeń...",
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

function createHeroCard(hero: ProgressHeroPresentation): HTMLElement {
  const card = document.createElement("article");
  card.className = "hero-card progress-hero-card reveal";
  card.setAttribute("aria-label", "Podsumowanie postępów");

  const copy = document.createElement("div");
  copy.className = "progress-hero__copy";

  const trendBadge = document.createElement("div");
  trendBadge.className = `progress-hero__badge progress-hero__badge--${hero.trendDirection}`;
  trendBadge.append(createIcon(hero.trendDirection === "down" ? "trend-down" : "trend-up"));
  const trendText = document.createElement("span");
  trendText.textContent = hero.trendLabel;
  trendBadge.append(trendText);

  const headline = document.createElement("h2");
  headline.className = "progress-hero__headline";
  headline.textContent = hero.headline;

  const sub = document.createElement("p");
  sub.className = "progress-hero__subheading";
  sub.textContent = hero.subheading;

  const timeframe = document.createElement("p");
  timeframe.className = "progress-hero__timeframe";
  timeframe.textContent = hero.timeframeText;

  copy.append(trendBadge, headline, sub, timeframe);
  card.append(copy);
  return card;
}

function createImprovementsSection(
  items: readonly ProgressImprovementItem[],
): HTMLElement {
  const section = createSection("Największe postępy", "biggest-improvements");
  section.classList.add("progress-improvements-section");

  const list = document.createElement("ul");
  list.className = "improvements-grid";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "improvement-card-item";

    const card = createCard("improvement-card");
    const iconBadge = document.createElement("span");
    iconBadge.className = "icon-badge icon-badge--recovery improvement-card__icon";
    iconBadge.setAttribute("aria-hidden", "true");
    iconBadge.append(createIcon(item.iconName));

    const content = document.createElement("div");
    content.className = "improvement-card__content";

    const titleRow = document.createElement("div");
    titleRow.className = "improvement-card__header";

    const title = document.createElement("h3");
    title.className = "improvement-card__title";
    title.textContent = item.title;

    const highlight = document.createElement("span");
    highlight.className = "improvement-card__highlight";
    highlight.textContent = item.highlightText;

    titleRow.append(title, highlight);

    const desc = document.createElement("p");
    desc.className = "improvement-card__description";
    desc.textContent = item.description;

    content.append(titleRow, desc);
    card.append(iconBadge, content);
    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createAreasToImproveSection(
  items: readonly ProgressAreaToImproveItem[],
): HTMLElement {
  const section = createSection("Obszary wymagające uwagi", "areas-to-improve");
  section.classList.add("progress-areas-section");

  const list = document.createElement("ul");
  list.className = "areas-grid";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "area-card-item";

    const card = createCard(`area-card area-card--${item.tone}`);

    const header = document.createElement("div");
    header.className = "area-card__header";

    const title = document.createElement("h3");
    title.className = "area-card__title";
    title.textContent = item.title;

    const tag = document.createElement("span");
    tag.className = "area-card__tag";
    tag.textContent = item.focusTag;

    header.append(title, tag);

    const guidance = document.createElement("p");
    guidance.className = "area-card__guidance";
    guidance.textContent = item.guidance;

    card.append(header, guidance);
    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createTrendSection(
  trend: ProgressTrendPresentation,
): HTMLElement {
  const section = createSection(trend.title, "progress-trend");
  section.classList.add("progress-trend-section");

  const card = createCard("trend-sparkline-card");

  const sub = document.createElement("p");
  sub.className = "trend-sparkline__description";
  sub.textContent = trend.description;

  const chart = document.createElement("div");
  chart.className = "sparkline-container";
  chart.setAttribute("role", "img");
  chart.setAttribute("aria-label", `${trend.title}: ${trend.periodText}`);

  const maxVal = Math.max(...trend.points.map((p) => p.value), 1);
  const minVal = Math.min(...trend.points.map((p) => p.value), 0);
  const range = Math.max(maxVal - minVal, 1);

  const bars = document.createElement("div");
  bars.className = "sparkline-bars";

  for (const point of trend.points) {
    const barCol = document.createElement("div");
    barCol.className = "sparkline-col";

    const valLabel = document.createElement("span");
    valLabel.className = "sparkline-val";
    valLabel.textContent = point.displayValue;

    const barTrack = document.createElement("div");
    barTrack.className = "sparkline-track";

    const pct = Math.max(15, Math.min(100, Math.round(((point.value - minVal) / range) * 85 + 15)));
    const barFill = document.createElement("span");
    barFill.className = "sparkline-fill";
    barFill.style.height = `${pct}%`;

    barTrack.append(barFill);

    const label = document.createElement("span");
    label.className = "sparkline-label";
    label.textContent = point.label;

    barCol.append(valLabel, barTrack, label);
    bars.append(barCol);
  }

  chart.append(bars);
  card.append(sub, chart);
  section.append(card);
  return section;
}

function createAISummarySection(
  summary: ProgressPresentation["aiSummary"],
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

function createTechnicalMetricsSection(
  tech: ProgressTechnicalMetricsPresentation,
): HTMLElement {
  const section = createSection(tech.title, "technical-metrics");
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

    if (metric.changeText) {
      const change = document.createElement("span");
      change.className = "metric-change-badge";
      change.textContent = metric.changeText;
      dd.append(change);
    }

    row.append(dt, dd);
    dl.append(row);
  }

  card.append(dl);
  section.append(card);
  return section;
}
