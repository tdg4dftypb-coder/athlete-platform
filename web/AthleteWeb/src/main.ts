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
  resolveBiomarkersPreviewState,
} from "./app/preview-state";
import {
  resolveApplicationView,
  resolveHistoryCode,
  searchForView,
  type ApplicationView,
} from "./app/view-routing";
import { bodyCompositionPreviewStates } from "./preview-data/body-composition-preview-data";
import { morningBriefingPreviewStates } from "./preview-data/morning-briefing-preview-data";
import { nutritionPreviewStates } from "./preview-data/nutrition-preview-data";
import { progressPreviewStates } from "./preview-data/progress-preview-data";
import { recoveryPreviewStates } from "./preview-data/recovery-preview-data";
import { trainingPreviewStates } from "./preview-data/training-preview-data";
import { biomarkersPreviewStates } from "./biomarkers/biomarkers-preview-data";
import { createBiomarkersExperienceApp } from "./biomarkers/biomarkers-experience-view";
import { HttpBiomarkersPayloadSource } from "./biomarkers/biomarkers-payload-source";
import { parseAndMapBiomarkersPayloadToPresentation } from "./biomarkers/biomarkers-mapper";
import { createHistoryExperienceApp } from "./biomarkers/history/history-experience-view";
import { HttpHistoryPayloadSource, HistoryNotFoundError } from "./biomarkers/history/history-payload-source";
import { parseHistoryPayloadV1 } from "./biomarkers/history/history-payload-parser";
import { mapHistoryPayloadToPresentation } from "./biomarkers/history/history-presentation";
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

import { HttpDashboardPayloadSource, StaticJsonDashboardPayloadSource } from "./app/dashboard-payload-source";
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

function getSourceMode(): "preview" | "live-file" | "http" {
  const source = new URLSearchParams(window.location.search).get("source");
  if (source === "live-file") return "live-file";
  if (source === "http") return "http";
  return "preview";
}

function renderPreview(focusHeading = false): void {
  const view = resolveApplicationView(window.location.search);
  const mode = getSourceMode();

  if (mode !== "preview") {
    renderExternalSourceView(view, mode, focusHeading);
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
  } else if (view === "biomarkers") {
    const state = resolveBiomarkersPreviewState(
      window.location.search,
      biomarkersPreviewStates,
    );
    appElement = createBiomarkersExperienceApp(state, openMorningBriefing, retry);
  } else if (view === "history") {
    const code = resolveHistoryCode(window.location.search);
    if (!code) {
      appElement = createHistoryExperienceApp(
        { kind: "unavailable", title: "Historia biomarkera", message: "Nie podano kodu biomarkera." },
        openBiomarkers,
      );
    } else {
      // Preview mode: show a ready state with synthetic data
      appElement = createHistoryExperienceApp(
        {
          kind: "ready",
          presentation: {
            title: code,
            unit: "",
            totalMeasurements: 0,
            latestMeasurement: null,
            measurements: [],
          },
        },
        openBiomarkers,
      );
    }
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

async function renderExternalSourceView(view: ApplicationView, mode: "live-file" | "http", focusHeading: boolean): Promise<void> {
  if (view === "history") {
    const code = resolveHistoryCode(window.location.search);
    const loadingEl = createHistoryExperienceApp(
      { kind: "loading", message: "Wczytywanie historii biomarkera..." },
      openBiomarkers,
    );
    loadingEl.classList.add("view-container");
    root.replaceChildren(loadingEl);

    try {
      if (!code) {
        const appElement = createHistoryExperienceApp(
          { kind: "unavailable", title: "Historia biomarkera", message: "Nie podano kodu biomarkera." },
          openBiomarkers,
        );
        appElement.classList.add("view-container");
        root.replaceChildren(appElement);
        return;
      }

      const source = new HttpHistoryPayloadSource("/api/v1/biomarkers/history");
      const rawData = await source.load(code);
      const parseResult = parseHistoryPayloadV1(rawData);

      let appElement: HTMLElement;
      if (!parseResult.success) {
        appElement = createHistoryExperienceApp(
          { kind: "failure", title: "Błąd danych", message: "Nie udało się przetworzyć historii biomarkera." },
          openBiomarkers,
        );
      } else {
        const presentation = mapHistoryPayloadToPresentation(parseResult.data, {
          locale: "pl-PL",
          timeZone: "Europe/Warsaw",
        });
        appElement = createHistoryExperienceApp(
          { kind: "ready", presentation },
          openBiomarkers,
        );
      }

      appElement.classList.add("view-container");
      root.replaceChildren(appElement);
      if (focusHeading) root.querySelector<HTMLElement>("h1")?.focus();
    } catch (error) {
      const isNotFound = error instanceof HistoryNotFoundError;
      const appElement = createHistoryExperienceApp(
        isNotFound
          ? { kind: "unavailable", title: code, message: "Brak historii pomiarów." }
          : { kind: "failure", title: "Błąd połączenia", message: "Nie udało się pobrać historii biomarkera." },
        openBiomarkers,
      );
      appElement.classList.add("view-container");
      root.replaceChildren(appElement);
    }
    return;
  }

  // Step 1: Render loading state
  let loadingElement: HTMLElement;
  if (view === "recovery") loadingElement = createRecoveryApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "training") loadingElement = createTrainingApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "progress") loadingElement = createProgressApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "nutrition") loadingElement = createNutritionApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "body") loadingElement = createBodyCompositionApp({ kind: "loading", message: "Wczytywanie..." }, openMorningBriefing, retry);
  else if (view === "biomarkers") loadingElement = createBiomarkersExperienceApp({ kind: "loading", message: "Wczytywanie biomarkerów..." }, openMorningBriefing, retry);
  else loadingElement = createApp({ kind: "loading", message: "Wczytywanie..." }, retry, openRecovery, openTraining, openProgress);

  loadingElement.classList.add("view-container");
  root.replaceChildren(loadingElement);

  try {
    if (view === "biomarkers") {
      const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");
      const rawData = await source.load();
      const state = parseAndMapBiomarkersPayloadToPresentation(rawData, previewMappingContext);
      const appElement = createBiomarkersExperienceApp(state, openMorningBriefing, retry);

      appElement.classList.add("view-container");
      root.replaceChildren(appElement);

      if (focusHeading) {
        const heading = root.querySelector<HTMLElement>("h1");
        heading?.focus();
      }
      return;
    }

    const payloadSource = mode === "http"
      ? new HttpDashboardPayloadSource()
      : new StaticJsonDashboardPayloadSource("/data/athlete-dashboard-v1.json");

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
    const errorText = error instanceof Error ? error.message : "Błąd pobierania danych.";
    const failureState = {
      kind: "failure" as const,
      title: "Błąd odczytu danych",
      message: mode === "http" ? "Nie udało się pobrać danych przez HTTP API." : "Nie udało się wczytać danych.",
      supportingText: `Błąd transportu: ${errorText}`,
      retryLabel: "Spróbuj ponownie",
    };

    let errorElement: HTMLElement;
    if (view === "biomarkers") errorElement = createBiomarkersExperienceApp(failureState, openMorningBriefing, retry);
    else if (view === "recovery") errorElement = createRecoveryApp({ ...failureState, header: { title: "Błąd", dateText: "", lastUpdatedText: "", freshnessLabel: null } }, openMorningBriefing, retry);
    else if (view === "training") errorElement = createTrainingApp({ ...failureState, header: { title: "Błąd", dateText: "", lastUpdatedText: "", freshnessLabel: null } }, openMorningBriefing, retry);
    else if (view === "progress") errorElement = createProgressApp({ ...failureState, header: { title: "Błąd", dateText: "", lastUpdatedText: "", freshnessLabel: null } }, openMorningBriefing, retry);
    else if (view === "nutrition") errorElement = createNutritionApp({ ...failureState, header: { title: "Błąd", dateText: "", lastUpdatedText: "", freshnessLabel: null } }, openMorningBriefing, retry);
    else if (view === "body") errorElement = createBodyCompositionApp({ ...failureState, header: { title: "Błąd", dateText: "", lastUpdatedText: "", freshnessLabel: null } }, openMorningBriefing, retry);
    else errorElement = createApp({ ...failureState, header: { greeting: "Błąd", athleteName: "", dateText: "", timeText: "" } }, retry, openRecovery, openTraining, openProgress);

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
    window.history.state?.athleteView === "body" ||
    window.history.state?.athleteView === "biomarkers" ||
    window.history.state?.athleteView === "history"
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

function openBiomarkers(): void {
  navigateTo("biomarkers");
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
