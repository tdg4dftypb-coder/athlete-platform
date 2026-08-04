import "./styles/reset.css";
import "./theme/tokens.css";
import "./styles/main.css";

import { createApp, createBodyCompositionApp, createNutritionApp, createProgressApp, createRecoveryApp, createTrainingApp } from "./app/create-app";
import { renderActivityIconGallery } from "./features/activity-icons/activity-icon-gallery-view";
import {
  resolveApplicationBodyState,
  resolveApplicationNutritionState,
  resolveApplicationPreviewState,
  resolveApplicationProgressState,
  resolveApplicationRecoveryState,
  resolveApplicationTrainingState,
} from "./app/preview-state";
import {
  resolveApplicationView,
  searchForView,
  type ApplicationView,
} from "./app/view-routing";
import { bodyCompositionPreviewStates } from "./preview-data/body-composition-preview-data";
import { morningBriefingPreviewStates } from "./preview-data/morning-briefing-preview-data";
import { nutritionPreviewStates } from "./preview-data/nutrition-preview-data";
import { progressPreviewStates } from "./preview-data/progress-preview-data";
import { recoveryPreviewStates } from "./preview-data/recovery-preview-data";
import { trainingPreviewStates } from "./preview-data/training-preview-data";
import { MORNING_BRIEFING_MAX_AGE_MS } from "./mappers/mapping-context";

const root = requireRoot();
const previewMappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: MORNING_BRIEFING_MAX_AGE_MS,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
} as const;

function requireRoot(): HTMLDivElement {
  const element = document.querySelector<HTMLDivElement>("#app");
  if (!element) throw new Error("Missing application root");
  return element;
}

import { renderMoreExperience } from "./features/more/more-view";

const scrollPositions = new Map<string, number>();

function saveScrollPosition(): void {
  const currentView = resolveApplicationView(window.location.search);
  scrollPositions.set(currentView, window.scrollY);
}

function restoreScrollPosition(view: ApplicationView): void {
  const savedY = scrollPositions.get(view) ?? 0;
  window.scrollTo({ top: savedY, behavior: "instant" as ScrollBehavior });
}

function renderPreview(focusHeading = false): void {
  const view = resolveApplicationView(window.location.search);
  let appElement: HTMLElement;

  if (view === "recovery") {
    const state = resolveApplicationRecoveryState(
      window.location.search,
      recoveryPreviewStates,
      previewMappingContext,
    );
    appElement = createRecoveryApp(state, openMorningBriefing, retry);
  } else if (view === "training") {
    const state = resolveApplicationTrainingState(
      window.location.search,
      trainingPreviewStates,
      previewMappingContext,
    );
    appElement = createTrainingApp(state, openMorningBriefing, retry);
  } else if (view === "progress") {
    const state = resolveApplicationProgressState(
      window.location.search,
      progressPreviewStates,
      previewMappingContext,
    );
    appElement = createProgressApp(state, openMorningBriefing, retry);
  } else if (view === "nutrition") {
    const state = resolveApplicationNutritionState(
      window.location.search,
      nutritionPreviewStates,
      previewMappingContext,
    );
    appElement = createNutritionApp(state, openMorningBriefing, retry);
  } else if (view === "body") {
    const state = resolveApplicationBodyState(
      window.location.search,
      bodyCompositionPreviewStates,
      previewMappingContext,
    );
    appElement = createBodyCompositionApp(state, openMorningBriefing, retry);
  } else if (view === "more") {
    appElement = renderMoreExperience(openMorningBriefing);
  } else if (view === "icons") {
    appElement = renderActivityIconGallery(openMorningBriefing);
  } else {
    const state = resolveApplicationPreviewState(
      window.location.search,
      morningBriefingPreviewStates,
      previewMappingContext,
    );
    appElement = createApp(state, retry, openRecovery, openTraining, openProgress);
  }

  appElement.classList.add("view-container");
  root.replaceChildren(appElement);

  if (focusHeading) {
    const heading = root.querySelector<HTMLElement>("h1");
    heading?.focus();
  }
}

function retry(): void {
  const url = new URL(window.location.href);
  url.searchParams.set("state", "ready");
  window.history.replaceState({}, "", url);
  renderPreview(true);
}

function openRecovery(): void {
  navigateTo("recovery");
}

function openTraining(): void {
  navigateTo("training");
}

function openProgress(): void {
  navigateTo("progress");
}

export function openNutrition(): void {
  navigateTo("nutrition");
}

export function openBody(): void {
  navigateTo("body");
}

function openMorningBriefing(): void {
  saveScrollPosition();
  if (
    window.history.state?.athleteView === "recovery" ||
    window.history.state?.athleteView === "training" ||
    window.history.state?.athleteView === "progress" ||
    window.history.state?.athleteView === "nutrition" ||
    window.history.state?.athleteView === "body"
  ) {
    window.history.back();
    return;
  }

  const url = new URL(window.location.href);
  url.search = searchForView(url.search, "morning-briefing");
  window.history.replaceState({ athleteView: "morning-briefing" }, "", url);
  renderPreview(true);
  restoreScrollPosition("morning-briefing");
}

function navigateTo(view: ApplicationView): void {
  saveScrollPosition();
  const url = new URL(window.location.href);
  url.search = searchForView(url.search, view);
  window.history.pushState({ athleteView: view }, "", url);
  renderPreview(true);
  restoreScrollPosition(view);
}

renderPreview();
window.addEventListener("popstate", () => {
  const view = resolveApplicationView(window.location.search);
  renderPreview(true);
  restoreScrollPosition(view);
});

