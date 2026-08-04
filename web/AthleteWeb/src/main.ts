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

import { StaticJsonDashboardPayloadSource } from "./app/dashboard-payload-source";
import { parseAndMapAthleteDashboardToMorningBriefing } from "./mappers/morning-briefing-mapper";
import { parseAndMapAthleteDashboardToRecovery } from "./mappers/recovery-mapper";
import { parseAndMapAthleteDashboardToTraining } from "./mappers/training-mapper";
import { parseAndMapAthleteDashboardToProgress } from "./mappers/progress-mapper";
import { parseAndMapAthleteDashboardToNutrition } from "./mappers/nutrition-mapper";
import { parseAndMapAthleteDashboardToBody } from "./mappers/body-composition-mapper";

const scrollPositions = new Map<string, number>();

function saveScrollPosition(): void {
  const currentView = resolveApplicationView(window.location.search);
  scrollPositions.set(currentView, window.scrollY);
}

function restoreScrollPosition(view: ApplicationView): void {
  const savedY = scrollPositions.get(view) ?? 0;
  window.scrollTo({ top: savedY, behavior: "instant" as ScrollBehavior });
}

function isLiveFileSource(): boolean {
  return new URLSearchParams(window.location.search).get("source") === "live-file";
}

function renderPreview(focusHeading = false): void {
  const view = resolveApplicationView(window.location.search);

  if (isLiveFileSource()) {
    renderLiveFileView(view, focusHeading);
    return;
  }

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

async function renderLiveFileView(view: ApplicationView, focusHeading: boolean): Promise<void> {
  // Step 1: Render loading state
  let loadingElement: HTMLElement;
  if (view === "recovery") loadingElement = createRecoveryApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "training") loadingElement = createTrainingApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "progress") loadingElement = createProgressApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "nutrition") loadingElement = createNutritionApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "body") loadingElement = createBodyCompositionApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else loadingElement = createApp({ kind: "loading", message: "Wczytywanie..." }, retry, openRecovery, openTraining, openProgress);

  loadingElement.classList.add("view-container");
  root.replaceChildren(loadingElement);

  try {
    const payloadSource = new StaticJsonDashboardPayloadSource("/data/athlete-dashboard-v1.json");
    const rawData = await payloadSource.load();

    let appElement: HTMLElement;
    if (view === "recovery") {
      const state = parseAndMapAthleteDashboardToRecovery(rawData, previewMappingContext);
      appElement = createRecoveryApp(state, openMorningBriefing, retry);
    } else if (view === "training") {
      const state = parseAndMapAthleteDashboardToTraining(rawData, previewMappingContext);
      appElement = createTrainingApp(state, openMorningBriefing, retry);
    } else if (view === "progress") {
      const state = parseAndMapAthleteDashboardToProgress(rawData, previewMappingContext);
      appElement = createProgressApp(state, openMorningBriefing, retry);
    } else if (view === "nutrition") {
      const state = parseAndMapAthleteDashboardToNutrition(rawData, previewMappingContext);
      appElement = createNutritionApp(state, openMorningBriefing, retry);
    } else if (view === "body") {
      const state = parseAndMapAthleteDashboardToBody(rawData, previewMappingContext);
      appElement = createBodyCompositionApp(state, openMorningBriefing, retry);
    } else if (view === "more") {
      appElement = renderMoreExperience(openMorningBriefing);
    } else if (view === "icons") {
      appElement = renderActivityIconGallery(openMorningBriefing);
    } else {
      const state = parseAndMapAthleteDashboardToMorningBriefing(rawData, previewMappingContext);
      appElement = createApp(state, retry, openRecovery, openTraining, openProgress);
    }

    appElement.classList.add("view-container");
    root.replaceChildren(appElement);

    if (focusHeading) {
      const heading = root.querySelector<HTMLElement>("h1");
      heading?.focus();
    }
  } catch (error) {
    const errorText = error instanceof Error ? error.message : "Błąd odczytu pliku.";
    const expHeader = {
      title: "Błąd odczytu danych",
      dateText: "Wystąpił błąd",
      lastUpdatedText: "Brak połączenia z plikiem payloadu",
      freshnessLabel: null,
    };
    const failureState = {
      kind: "failure" as const,
      header: expHeader,
      message: "Nie udało się wczytać pliku payloadu v1.0.",
      supportingText: `Błąd transportu lub brak pliku: ${errorText}`,
      retryLabel: "Spróbuj ponownie",
    };

    const briefingFailureState = {
      kind: "failure" as const,
      header: {
        greeting: "Dzień dobry",
        athleteName: previewMappingContext.athleteName,
        dateText: "Wystąpił błąd",
        timeText: "--:--",
      },
      message: "Nie udało się wczytać pliku payloadu v1.0.",
      supportingText: `Błąd transportu lub brak pliku: ${errorText}`,
      retryLabel: "Spróbuj ponownie",
    };

    let errorElement: HTMLElement;
    if (view === "recovery") errorElement = createRecoveryApp(failureState, openMorningBriefing, retry);
    else if (view === "training") errorElement = createTrainingApp(failureState, openMorningBriefing, retry);
    else if (view === "progress") errorElement = createProgressApp(failureState, openMorningBriefing, retry);
    else if (view === "nutrition") errorElement = createNutritionApp(failureState, openMorningBriefing, retry);
    else if (view === "body") errorElement = createBodyCompositionApp(failureState, openMorningBriefing, retry);
    else errorElement = createApp(briefingFailureState, retry, openRecovery, openTraining, openProgress);

    errorElement.classList.add("view-container");
    root.replaceChildren(errorElement);
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

