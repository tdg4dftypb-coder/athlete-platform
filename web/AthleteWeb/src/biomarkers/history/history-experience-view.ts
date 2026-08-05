/**
 * Sprint 7F — Biomarker History Experience View
 *
 * Renders 4 presentation states: loading | ready | failure | unavailable.
 * Consumes only HistoryPresentation — no knowledge of HTTP payload or backend.
 */

import { createBottomNavigation } from "../../components/bottom-navigation";
import { createPageHeader } from "../../components/page-header";
import type { HistoryPresentationState, HistoryPresentation, HistoryMeasurementPresentation } from "./history-presentation";

export function createHistoryExperienceApp(
  state: HistoryPresentationState,
  onBackToBiomarkers: () => void,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell history-shell";

  const main = document.createElement("main");
  main.className = "briefing history-view";

  // Page header
  const pageHeader = createPageHeader(
    {
      title: getHeaderTitle(state),
      dateText: "",
      lastUpdatedText: getHeaderSubtitle(state),
      freshnessLabel: null,
    },
    onBackToBiomarkers,
  );
  main.appendChild(pageHeader);

  // Content based on state
  switch (state.kind) {
    case "loading":
      main.appendChild(renderLoading(state.message));
      break;

    case "failure":
      main.appendChild(renderFailure(state.title, state.message));
      break;

    case "unavailable":
      main.appendChild(renderUnavailable(state.title, state.message));
      break;

    case "ready":
      renderReady(main, state.presentation);
      break;
  }

  shell.append(main, createBottomNavigation({ currentView: "biomarkers" }));
  return shell;
}

// ---------------------------------------------------------------------------
// State renderers
// ---------------------------------------------------------------------------

function renderLoading(message: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "card card-loading history-skeleton";
  section.setAttribute("aria-busy", "true");
  section.setAttribute("aria-live", "polite");
  section.innerHTML = `
    <p style="color: var(--color-text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">${escapeHtml(message)}</p>
    <div style="height: 5rem; background: var(--color-surface-muted); border-radius: 10px; margin-bottom: 1rem; animation: pulse 1.4s ease-in-out infinite;"></div>
    <div style="height: 3rem; background: var(--color-surface-muted); border-radius: 8px; margin-bottom: 0.6rem; animation: pulse 1.4s ease-in-out infinite; animation-delay: 0.1s;"></div>
    <div style="height: 3rem; background: var(--color-surface-muted); border-radius: 8px; animation: pulse 1.4s ease-in-out infinite; animation-delay: 0.2s;"></div>
  `;
  return section;
}

function renderFailure(title: string, message: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "card card-failure";
  section.setAttribute("aria-live", "assertive");

  const h2 = document.createElement("h2");
  h2.style.cssText = "font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem;";
  h2.textContent = title;

  const p = document.createElement("p");
  p.style.cssText = "color: var(--color-text-secondary); font-size: 0.9rem;";
  p.textContent = message;

  section.append(h2, p);
  return section;
}

function renderUnavailable(title: string, message: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "card card-unavailable";
  section.style.cssText = "text-align: center; padding: 2rem 1.2rem;";

  const h2 = document.createElement("h2");
  h2.style.cssText = "font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem;";
  h2.textContent = title;

  const p = document.createElement("p");
  p.style.cssText = "color: var(--color-text-secondary); font-size: 0.9rem;";
  p.textContent = message;

  section.append(h2, p);
  return section;
}

function renderReady(main: HTMLElement, presentation: HistoryPresentation): void {
  // Hero card — latest measurement
  if (presentation.latestMeasurement) {
    main.appendChild(renderHeroCard(presentation.title, presentation.latestMeasurement));
  }

  // Full measurements list
  const listSection = document.createElement("section");
  listSection.className = "card card-history-list";

  const listTitle = document.createElement("h2");
  listTitle.style.cssText = "font-size: 1rem; font-weight: 700; margin-bottom: 0.8rem;";
  listTitle.textContent = `Historia pomiarów (${presentation.totalMeasurements})`;
  listSection.appendChild(listTitle);

  if (presentation.measurements.length === 0) {
    const empty = document.createElement("p");
    empty.style.cssText = "color: var(--color-text-secondary); font-size: 0.9rem; text-align: center; padding: 1rem 0;";
    empty.textContent = "Brak historii pomiarów.";
    listSection.appendChild(empty);
  } else {
    const ul = document.createElement("ul");
    ul.style.cssText = "list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.65rem;";

    // Display newest → oldest for intuitive reading (reverse the already-ordered list)
    const displayOrder = [...presentation.measurements].reverse();

    for (const m of displayOrder) {
      ul.appendChild(renderMeasurementRow(m));
    }

    listSection.appendChild(ul);
  }

  main.appendChild(listSection);
}

// ---------------------------------------------------------------------------
// Sub-component renderers
// ---------------------------------------------------------------------------

function renderHeroCard(
  biomarkerName: string,
  latest: HistoryMeasurementPresentation,
): HTMLElement {
  const card = document.createElement("section");
  card.className = "card card-hero history-hero";
  card.setAttribute("aria-label", `Ostatni wynik: ${biomarkerName}`);

  const label = document.createElement("p");
  label.style.cssText =
    "font-size: 0.78rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.3rem;";
  label.textContent = "Ostatni wynik";

  const valueRow = document.createElement("div");
  valueRow.style.cssText =
    "display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.4rem;";

  const valueBig = document.createElement("span");
  valueBig.style.cssText =
    "font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; color: var(--color-text-primary);";
  valueBig.textContent = latest.valueLabel;

  valueRow.appendChild(valueBig);

  const meta = document.createElement("div");
  meta.style.cssText =
    "display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.82rem; color: var(--color-text-secondary); align-items: center;";

  const dateSpan = document.createElement("span");
  dateSpan.textContent = latest.collectedAtLabel;
  meta.appendChild(dateSpan);

  if (latest.flagLabel) {
    const flagBadge = document.createElement("span");
    flagBadge.style.cssText =
      "font-weight: 600; padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--color-surface-elevated); border: 1px solid var(--color-border); font-size: 0.78rem;";
    flagBadge.textContent = latest.flagLabel;
    meta.appendChild(flagBadge);
  }

  const verSpan = document.createElement("span");
  verSpan.textContent = `• ${latest.verificationLabel}`;
  meta.appendChild(verSpan);

  card.append(label, valueRow, meta);
  return card;
}

function renderMeasurementRow(m: HistoryMeasurementPresentation): HTMLElement {
  const li = document.createElement("li");
  li.className = "history-measurement-row";
  li.style.cssText =
    "padding: 0.75rem 0.9rem; border-radius: 8px; background: var(--color-surface-muted); display: flex; flex-direction: column; gap: 0.3rem; border-left: 3px solid var(--color-border);";

  const topRow = document.createElement("div");
  topRow.style.cssText =
    "display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.4rem;";

  const dateEl = document.createElement("span");
  dateEl.style.cssText = "font-size: 0.82rem; color: var(--color-text-secondary); font-weight: 500;";
  dateEl.textContent = m.collectedAtLabel;

  const valEl = document.createElement("span");
  valEl.style.cssText = "font-weight: 700; font-size: 0.95rem;";
  valEl.textContent = m.valueLabel;

  topRow.append(dateEl, valEl);

  const bottomRow = document.createElement("div");
  bottomRow.style.cssText =
    "display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.78rem; color: var(--color-text-secondary); align-items: center;";

  if (m.flagLabel) {
    const flagEl = document.createElement("span");
    flagEl.style.cssText =
      "font-weight: 600; padding: 0.1rem 0.35rem; border-radius: 4px; background: var(--color-surface-elevated); border: 1px solid var(--color-border);";
    flagEl.textContent = m.flagLabel;
    bottomRow.appendChild(flagEl);
  }

  const verEl = document.createElement("span");
  verEl.textContent = m.verificationLabel;
  bottomRow.appendChild(verEl);

  li.append(topRow, bottomRow);
  return li;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getHeaderTitle(state: HistoryPresentationState): string {
  if (state.kind === "ready") return state.presentation.title;
  if (state.kind === "unavailable") return state.title;
  return "Historia biomarkera";
}

function getHeaderSubtitle(state: HistoryPresentationState): string {
  if (state.kind === "ready") {
    const n = state.presentation.totalMeasurements;
    return `${n} ${measurementWord(n)}`;
  }
  if (state.kind === "loading") return state.message;
  return "";
}

function measurementWord(n: number): string {
  if (n === 1) return "pomiar";
  if (n >= 2 && n <= 4) return "pomiary";
  return "pomiarów";
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
