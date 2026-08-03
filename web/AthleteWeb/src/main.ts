import "./styles/reset.css";
import "./theme/tokens.css";
import "./styles/main.css";

import { createApp } from "./app/create-app";
import { resolveApplicationPreviewState } from "./app/preview-state";
import { morningBriefingPreviewStates } from "./preview-data/morning-briefing-preview-data";
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
  const state = resolveApplicationPreviewState(
    window.location.search,
    morningBriefingPreviewStates,
    previewMappingContext,
  );
  root.replaceChildren(createApp(state, retry));

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

renderPreview();
