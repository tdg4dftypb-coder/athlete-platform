import "./styles/reset.css";
import "./theme/tokens.css";
import "./styles/main.css";

import { createApp, createRecoveryApp } from "./app/create-app";
import {
  resolveApplicationPreviewState,
  resolveApplicationRecoveryState,
} from "./app/preview-state";
import {
  resolveApplicationView,
  searchForView,
  type ApplicationView,
} from "./app/view-routing";
import { morningBriefingPreviewStates } from "./preview-data/morning-briefing-preview-data";
import { recoveryPreviewStates } from "./preview-data/recovery-preview-data";
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

function renderPreview(focusHeading = false): void {
  const view = resolveApplicationView(window.location.search);
  if (view === "recovery") {
    const state = resolveApplicationRecoveryState(
      window.location.search,
      recoveryPreviewStates,
      previewMappingContext,
    );
    root.replaceChildren(createRecoveryApp(state, openMorningBriefing, retry));
  } else {
    const state = resolveApplicationPreviewState(
      window.location.search,
      morningBriefingPreviewStates,
      previewMappingContext,
    );
    root.replaceChildren(createApp(state, retry, openRecovery));
  }

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

function openMorningBriefing(): void {
  if (window.history.state?.athleteView === "recovery") {
    window.history.back();
    return;
  }

  const url = new URL(window.location.href);
  url.search = searchForView(url.search, "morning-briefing");
  window.history.replaceState({ athleteView: "morning-briefing" }, "", url);
  renderPreview(true);
}

function navigateTo(view: ApplicationView): void {
  const url = new URL(window.location.href);
  url.search = searchForView(url.search, view);
  window.history.pushState({ athleteView: view }, "", url);
  renderPreview(true);
}

renderPreview();
window.addEventListener("popstate", () => renderPreview(true));
