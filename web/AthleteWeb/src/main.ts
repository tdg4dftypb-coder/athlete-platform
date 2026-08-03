import "./styles/reset.css";
import "./theme/tokens.css";
import "./styles/main.css";

import { createApp } from "./app/create-app";
import { resolvePreviewState } from "./app/preview-state";
import { morningBriefingPreviewStates } from "./preview-data/morning-briefing-preview-data";

const root = requireRoot();

function requireRoot(): HTMLDivElement {
  const element = document.querySelector<HTMLDivElement>("#app");
  if (!element) throw new Error("Missing application root");
  return element;
}

function renderPreview(focusHeading = false): void {
  const state = resolvePreviewState(window.location.search, morningBriefingPreviewStates);
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
