import { createBottomNavigation } from "../../components/bottom-navigation";
import { createCard, createSection } from "../../components/card";
import { createIcon } from "../../components/icon";
import { createPageHeader } from "../../components/page-header";
import { createStatusNotice } from "../../components/status-notice";
import type {
  BodyCompositionBreakdownItem,
  BodyCompositionDataQualityPresentation,
  BodyCompositionGoalAlignmentPresentation,
  BodyCompositionHeroPresentation,
  BodyCompositionKeyChangeItem,
  BodyCompositionPresentation,
  BodyCompositionTechnicalPresentation,
  BodyCompositionTrendPresentation,
} from "../../models/body-composition-presentation";
import type { BodyCompositionPresentationState } from "../../models/body-composition-presentation-state";

export function renderBodyCompositionExperience(
  state: BodyCompositionPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell body-shell";
  shell.append(
    createStateContent(state, onBack, onRetry),
    createBottomNavigation({ currentView: "body" }),
  );

  return shell;
}

function createStateContent(
  state: BodyCompositionPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing body-view";

  switch (state.kind) {
    case "ready":
      appendAvailableBody(main, state.body, onBack);
      break;
    case "partial":
      main.append(createPageHeader(state.body.header, onBack));
      main.append(
        createStatusNotice({
          variant: "partial",
          title: "Częściowe dane o składzie ciała",
          message: state.message,
          detailLabel: "Brakuje:",
          details: state.missingData,
        }),
      );
      appendBodyContent(main, state.body);
      break;
    case "stale":
      main.append(createPageHeader(state.body.header, onBack));
      main.append(
        createStatusNotice({
          variant: "stale",
          title: "Dane wymagają odświeżenia",
          message: state.message,
          details: [state.lastUpdatedText],
        }),
      );
      appendBodyContent(main, state.body);
      break;
    case "unavailable":
      main.classList.add("briefing--message");
      main.append(
        createPageHeader(state.header, onBack),
        createStatusNotice({
          variant: "unavailable",
          title: "Skład ciała jest niedostępny",
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

function appendAvailableBody(
  main: HTMLElement,
  model: BodyCompositionPresentation,
  onBack: () => void,
): void {
  main.append(createPageHeader(model.header, onBack));
  appendBodyContent(main, model);
}

function appendBodyContent(
  main: HTMLElement,
  model: BodyCompositionPresentation,
): void {
  main.append(
    createHeroCard(model.hero),
    createKeyChangesSection(model.keyChanges),
    createTrendSection(model.trend),
    createBreakdownSection(model.breakdown),
    createGoalAlignmentSection(model.goalAlignment),
    createDataQualitySection(model.dataQuality),
    createPlaceholderSection(model.placeholderNote),
    createTechnicalSection(model.technical),
  );
}

function createLoadingContent(message: string, onBack: () => void): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing briefing--loading body-view";
  main.setAttribute("aria-busy", "true");

  const header = createPageHeader(
    {
      title: "Skład ciała",
      dateText: "Wczytywanie...",
      lastUpdatedText: "Analizowanie pomiarów i składu tkankowego...",
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

function createHeroCard(hero: BodyCompositionHeroPresentation): HTMLElement {
  const card = document.createElement("article");
  card.className = "hero-card body-hero-card reveal";
  card.setAttribute("aria-label", "Podsumowanie składu ciała");

  const copy = document.createElement("div");
  copy.className = "body-hero__copy";

  const badge = document.createElement("div");
  badge.className = `body-hero__badge body-hero__badge--${hero.goalStatusVariant}`;
  badge.append(createIcon(hero.trendDirection === "down" ? "trend-down" : "trend-up"));
  const badgeText = document.createElement("span");
  badgeText.textContent = `${hero.trendLabel} • ${hero.goalStatusBadgeText}`;
  badge.append(badgeText);

  const headline = document.createElement("h2");
  headline.className = "body-hero__headline";
  headline.textContent = hero.headline;

  const sub = document.createElement("p");
  sub.className = "body-hero__subheading";
  sub.textContent = hero.subheading;

  const timeframe = document.createElement("p");
  timeframe.className = "body-hero__timeframe";
  timeframe.textContent = hero.timeframeText;

  copy.append(badge, headline, sub, timeframe);
  card.append(copy);
  return card;
}

function createKeyChangesSection(
  items: readonly BodyCompositionKeyChangeItem[],
): HTMLElement {
  const section = createSection("Najważniejsze zmiany", "key-body-changes");
  section.classList.add("body-changes-section");

  const list = document.createElement("ul");
  list.className = "changes-grid";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "change-card-item";

    const card = createCard("change-card");

    const iconBadge = document.createElement("span");
    iconBadge.className = "icon-badge icon-badge--recovery change-card__icon";
    iconBadge.setAttribute("aria-hidden", "true");
    iconBadge.append(createIcon(item.iconName));

    const content = document.createElement("div");
    content.className = "change-card__content";

    const header = document.createElement("div");
    header.className = "change-card__header";

    const title = document.createElement("h3");
    title.className = "change-card__title";
    title.textContent = item.label;

    if (item.valueText) {
      const val = document.createElement("span");
      val.className = "change-card__value";
      val.textContent = item.valueText;
      header.append(title, val);
    } else {
      header.append(title);
    }

    const desc = document.createElement("p");
    desc.className = "change-card__desc";
    desc.textContent = item.description;

    const period = document.createElement("small");
    period.className = "change-card__period";
    period.textContent = item.periodText;

    content.append(header, desc, period);

    if (item.qualityNote) {
      const note = document.createElement("small");
      note.className = "change-card__quality";
      note.textContent = item.qualityNote;
      content.append(note);
    }

    card.append(iconBadge, content);
    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createTrendSection(
  trend: BodyCompositionTrendPresentation,
): HTMLElement {
  const section = createSection(trend.title, "body-mass-trend");
  section.classList.add("body-trend-section");

  const card = createCard("trend-sparkline-card");

  const sub = document.createElement("p");
  sub.className = "trend-sparkline__description";
  sub.textContent = trend.description;

  card.append(sub);

  if (!trend.isAvailable) {
    const notice = document.createElement("p");
    notice.className = "trend-unavailable-notice";
    notice.textContent = trend.unavailableMessage ?? "Brak danych trendu.";
    card.append(notice);
    section.append(card);
    return section;
  }

  if (trend.paceText || trend.weeklyAverageText) {
    const infoRow = document.createElement("div");
    infoRow.className = "trend-info-row";

    if (trend.paceText) {
      const pace = document.createElement("span");
      pace.className = "trend-pace-pill";
      pace.textContent = `Tempo: ${trend.paceText}`;
      infoRow.append(pace);
    }

    if (trend.weeklyAverageText) {
      const avg = document.createElement("span");
      avg.className = "trend-avg-text";
      avg.textContent = trend.weeklyAverageText;
      infoRow.append(avg);
    }

    card.append(infoRow);
  }

  const chart = document.createElement("div");
  chart.className = "sparkline-container";
  chart.setAttribute("role", "img");
  chart.setAttribute("aria-label", trend.title);

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
  card.append(chart);
  section.append(card);
  return section;
}

function createBreakdownSection(
  items: readonly BodyCompositionBreakdownItem[],
): HTMLElement {
  const section = createSection("Kompozycja ciała", "body-breakdown");
  section.classList.add("body-breakdown-section");

  const list = document.createElement("ul");
  list.className = "breakdown-grid";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "breakdown-card-item";

    const card = createCard("breakdown-card");

    const labelRow = document.createElement("div");
    labelRow.className = "breakdown-card__header";

    const label = document.createElement("span");
    label.className = "breakdown-card__label";
    label.textContent = item.label;

    if (item.statusTag) {
      const tag = document.createElement("span");
      tag.className = "breakdown-card__tag";
      tag.textContent = item.statusTag;
      labelRow.append(label, tag);
    } else {
      labelRow.append(label);
    }

    const value = document.createElement("strong");
    value.className = "breakdown-card__value";
    value.textContent = item.valueText;

    card.append(labelRow, value);

    if (item.subtext) {
      const sub = document.createElement("small");
      sub.className = "breakdown-card__subtext";
      sub.textContent = item.subtext;
      card.append(sub);
    }

    li.append(card);
    list.append(li);
  }

  section.append(list);
  return section;
}

function createGoalAlignmentSection(
  goal: BodyCompositionGoalAlignmentPresentation,
): HTMLElement {
  const section = createSection(goal.title, "goal-alignment");
  section.classList.add("goal-alignment-section");

  const card = createCard(`goal-alignment-card goal-alignment-card--${goal.alignmentVariant}`);

  const msg = document.createElement("p");
  msg.className = "goal-alignment__message";
  msg.textContent = goal.statusMessage;

  const list = document.createElement("ul");
  list.className = "goal-alignment__list";

  for (const detail of goal.details) {
    const li = document.createElement("li");
    li.textContent = detail;
    list.append(li);
  }

  card.append(msg, list);
  section.append(card);
  return section;
}

function createDataQualitySection(
  quality: BodyCompositionDataQualityPresentation,
): HTMLElement {
  const section = createSection(quality.title, "data-quality");
  section.classList.add("data-quality-section");

  const card = createCard("data-quality-card");

  const header = document.createElement("div");
  header.className = "data-quality__header";

  const status = document.createElement("strong");
  status.textContent = quality.isComplete ? "Kompletne dane" : "Ograniczenia danych";
  status.className = quality.isComplete ? "quality-tag quality-tag--complete" : "quality-tag quality-tag--partial";

  if (quality.completenessScoreText) {
    const score = document.createElement("span");
    score.className = "quality-score";
    score.textContent = quality.completenessScoreText;
    header.append(status, score);
  } else {
    header.append(status);
  }

  card.append(header);

  if (quality.limitations.length > 0) {
    const list = document.createElement("ul");
    list.className = "quality-limitations-list";

    for (const lim of quality.limitations) {
      const li = document.createElement("li");
      li.textContent = lim;
      list.append(li);
    }

    card.append(list);
  }

  section.append(card);
  return section;
}

function createPlaceholderSection(text: string | null): HTMLElement | DocumentFragment {
  if (!text) return document.createDocumentFragment();
  const section = createSection("Zapowiedź funkcji", "body-placeholder");
  section.className = "section placeholder-section";

  const card = createCard("placeholder-card");
  const icon = document.createElement("span");
  icon.className = "placeholder-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.append(createIcon("more"));

  const copy = document.createElement("div");
  const title = document.createElement("h3");
  title.className = "placeholder-title";
  title.textContent = text;
  const desc = document.createElement("p");
  desc.className = "placeholder-desc";
  desc.textContent = "W przyszłych wersjach: podgląd wizualnych stref redukcji tkanki tłuszczowej.";
  copy.append(title, desc);

  card.append(icon, copy);
  section.append(card);
  return section;
}

function createTechnicalSection(
  tech: BodyCompositionTechnicalPresentation,
): HTMLElement {
  const section = createSection(tech.title, "technical-body");
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

    row.append(dt, dd);
    dl.append(row);
  }

  card.append(dl);
  section.append(card);
  return section;
}
