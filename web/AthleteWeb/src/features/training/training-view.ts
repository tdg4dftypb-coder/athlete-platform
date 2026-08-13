import { createCard, createSection } from "../../components/card";
import { createPageHeader } from "../../components/page-header";
import { createStatusNotice } from "../../components/status-notice";
import { createBottomNavigation } from "../../components/bottom-navigation";
import { createIcon, type IconName } from "../../components/icon";
import type {
  TechnicalDetailsPresentation,
  TrainingHeroPresentation,
  TrainingPresentation,
  WorkoutBlockPresentation,
} from "../../models/training-presentation";

import type { TrainingPresentationState } from "../../models/training-presentation-state";
import type {
  TrainingPlanVisibility,
  VisiblePlannedSession,
} from "../../training-plan-visibility/training-plan-visibility";

export function renderTrainingExperience(
  state: TrainingPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell training-shell";
  shell.append(
    createStateContent(state, onBack, onRetry),
    createBottomNavigation({ currentView: "training" }),
  );

  return shell;
}

function createStateContent(
  state: TrainingPresentationState,
  onBack: () => void,
  onRetry: () => void,
): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing training-view";

  switch (state.kind) {
    case "ready":
      appendAvailableTraining(main, state.training, onBack);
      break;
    case "partial":
      main.append(createPageHeader(state.training.header, onBack));
      main.append(
        createStatusNotice({
          variant: "partial",
          title: "Niepełne dane treningu",
          message: state.message,
          detailLabel: "Brakuje:",
          details: state.missingData,
        }),
      );
      appendTrainingBody(main, state.training);
      break;
    case "stale":
      main.append(createPageHeader(state.training.header, onBack));
      main.append(
        createStatusNotice({
          variant: "stale",
          title: "Dane wymagają odświeżenia",
          message: state.message,
          details: [state.lastUpdatedText],
        }),
      );
      appendTrainingBody(main, state.training);
      break;
    case "unavailable":
      main.classList.add("briefing--message");
      main.append(
        createPageHeader(state.header, onBack),
        createStatusNotice({
          variant: "unavailable",
          title: "Trening jest dziś niedostępny",
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

function appendAvailableTraining(
  main: HTMLElement,
  model: TrainingPresentation,
  onBack: () => void,
): void {
  main.append(createPageHeader(model.header, onBack));
  appendTrainingBody(main, model);
}


function appendTrainingBody(
  main: HTMLElement,
  model: TrainingPresentation,
): void {
  main.append(
    createHeroCard(model.hero),
    createObjectiveSection(model.objective),
    createStructureSection(model.structure),
    createNotesSection(model.notes),
    createExpectedOutcomeSection(model.expectedOutcome),
  );

  if (model.technicalDetails) {
    main.append(createTechnicalDetailsSection(model.technicalDetails));
  }
  if (model.planVisibility) {
    main.append(createTrainingPlanVisibilitySection(model.planVisibility));
  }
}

function createTrainingPlanVisibilitySection(model: TrainingPlanVisibility): HTMLElement {
  const section = createSection("Training Plan & Runtime", "training-plan-runtime");
  section.classList.add("training-plan-runtime-section");
  const card = createCard("training-plan-runtime-card");
  card.append(
    createVisibilityGroup("Training Plan", [
      ["Plan", model.planId ?? "unavailable"],
      ["Version", model.version === null ? "unavailable" : `v${model.version}`],
      ["Coverage", model.startDate && model.endDate ? `${model.startDate} → ${model.endDate}` : "unavailable"],
      ["Future buffer", model.futureBufferDays === null ? "unavailable" : `${model.futureBufferDays} days`],
      ["Continuity", phaseStatus(model, "plan_horizon_continuity")],
      ["Plan transition", versionTransition(model.runtime?.continuity ?? null)],
    ]),
    createTodayGroup(model),
    createVisibilityGroup("Adaptation", [
      ["Status", phaseStatus(model, "plan_adaptation")],
      ["Outcome", model.runtime?.adaptation?.outcome ?? "unavailable"],
      ["Source / result version", versionTransition(model.runtime?.adaptation ?? null)],
    ]),
    createVisibilityGroup("Production Runtime", [
      ["Overall", model.runtime ? `${model.runtime.status} · r${model.runtime.revision}` : "unavailable"],
      ["PLAN_PRESCRIPTION", phaseStatus(model, "plan_prescription")],
      ["PLAN_HORIZON_CONTINUITY", phaseStatus(model, "plan_horizon_continuity")],
      ["PLAN_ADAPTATION", phaseStatus(model, "plan_adaptation")],
      ["MORNING_BRIEFING", phaseStatus(model, "morning_briefing")],
      ["PUBLICATION", phaseStatus(model, "publication")],
    ]),
  );
  if (model.limitations.length > 0) {
    const note = document.createElement("p");
    note.className = "visibility-limitations";
    note.textContent = model.limitations.join(" ");
    card.append(note);
  }
  section.append(card);
  return section;
}

function phaseStatus(
  model: TrainingPlanVisibility,
  name: keyof NonNullable<TrainingPlanVisibility["runtime"]>["phases"],
): string {
  const phase = model.runtime?.phases[name];
  if (!phase?.available) return "unavailable";
  const changed = phase.changedState === null ? "" : ` · changed: ${phase.changedState ? "yes" : "no"}`;
  const codes = phase.codes.length === 0 ? "" : ` · ${phase.codes.join(", ")}`;
  return `${phase.status ?? "unavailable"}${changed}${codes}`;
}

function versionTransition(value: { readonly sourceVersion: number | null; readonly resultVersion: number | null } | null): string {
  if (value?.sourceVersion === null || value?.sourceVersion === undefined) return "unavailable";
  return value.resultVersion === null ? `v${value.sourceVersion}` : `v${value.sourceVersion} → v${value.resultVersion}`;
}

function createTodayGroup(model: TrainingPlanVisibility): HTMLElement {
  const group = document.createElement("section");
  group.className = "visibility-group";
  const title = document.createElement("h3");
  title.textContent = "Today";
  group.append(title);

  const sessions = document.createElement("div");
  sessions.className = "visibility-session-list";
  if (model.sessions.length === 0) {
    sessions.textContent = "Sessions: unavailable";
  } else {
    model.sessions.forEach((session) => sessions.append(createSessionRow(session)));
  }
  group.append(sessions);

  const prescription = document.createElement("p");
  prescription.className = "visibility-inline-fact";
  prescription.textContent = model.prescription
    ? `Prescription: ${model.prescription.sessionType ?? model.prescription.disposition} · ${model.prescription.durationMinutes ?? "—"} min`
    : "Prescription: unavailable";
  group.append(prescription);

  if (model.reconciliation.length === 0) {
    const empty = document.createElement("p");
    empty.className = "visibility-inline-fact";
    empty.textContent = "Outcome / reconciliation: unavailable";
    group.append(empty);
  } else {
    model.reconciliation.forEach((item) => {
      const row = document.createElement("p");
      row.className = "visibility-inline-fact";
      row.textContent = `Outcome: ${item.plannedSessionId ?? "unplanned activity"} · ${item.matchStatus} · ${item.executionOutcome ?? "unavailable"}`;
      group.append(row);
    });
  }
  return group;
}

function createSessionRow(session: VisiblePlannedSession): HTMLElement {
  const row = document.createElement("article");
  row.className = "visibility-session";
  row.dataset.sessionId = session.sessionId;
  const heading = document.createElement("strong");
  heading.textContent = session.sessionType ?? session.kind;
  const details = document.createElement("span");
  details.textContent = `${session.durationMinutes} min · ${session.targetTss ?? "—"} TSS`;
  const identity = document.createElement("code");
  identity.textContent = session.sessionId;
  row.append(heading, details, identity);
  return row;
}

function createVisibilityGroup(
  titleText: string,
  rows: readonly (readonly [string, string])[],
): HTMLElement {
  const group = document.createElement("section");
  group.className = "visibility-group";
  const title = document.createElement("h3");
  title.textContent = titleText;
  const list = document.createElement("dl");
  list.className = "visibility-facts";
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = value;
    if (value === "unavailable") description.className = "is-unavailable";
    row.append(term, description);
    list.append(row);
  });
  group.append(title, list);
  return group;
}

function createLoadingContent(message: string, onBack: () => void): HTMLElement {
  const main = document.createElement("main");
  main.className = "briefing briefing--loading training-view";
  main.setAttribute("aria-busy", "true");

  const header = createPageHeader(
    {
      title: "Trening",
      dateText: "Wczytywanie...",
      lastUpdatedText: "Pobieranie danych planu...",
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

function createHeroCard(hero: TrainingHeroPresentation): HTMLElement {
  const card = document.createElement("article");
  card.className = "hero-card training-hero-card reveal";
  card.setAttribute("aria-label", `Podsumowanie treningu: ${hero.title}`);

  const headerRow = document.createElement("div");
  headerRow.className = "training-hero__header";

  const iconBadge = document.createElement("span");
  iconBadge.className = "icon-badge icon-badge--training training-hero__icon";
  iconBadge.setAttribute("aria-hidden", "true");
  iconBadge.append(createIcon(hero.activityIcon));

  const copy = document.createElement("div");
  copy.className = "training-hero__copy";

  const title = document.createElement("h2");
  title.className = "training-hero__title";
  title.textContent = hero.title;

  const desc = document.createElement("p");
  desc.className = "training-hero__description";
  desc.textContent = hero.description;

  copy.append(title, desc);
  headerRow.append(iconBadge, copy);

  const pillsRow = document.createElement("div");
  pillsRow.className = "training-hero__pills";

  const durationPill = createPill("history", hero.durationText, "Czas trwania");
  const intensityPill = createPill("gauge", hero.intensityText, "Intensywność");
  const targetPill = createPill("target", hero.targetGoalText, "Główny cel");


  pillsRow.append(durationPill, intensityPill, targetPill);

  card.append(headerRow, pillsRow);
  return card;
}

function createPill(
  iconName: IconName,
  text: string,
  ariaLabel: string,
): HTMLElement {
  const pill = document.createElement("span");
  pill.className = "training-pill";
  pill.setAttribute("aria-label", `${ariaLabel}: ${text}`);

  const icon = createIcon(iconName);
  icon.setAttribute("aria-hidden", "true");

  const label = document.createElement("span");
  label.textContent = text;

  pill.append(icon, label);
  return pill;
}

function createObjectiveSection(objective: string): HTMLElement {
  const section = createSection("Cel dzisiejszego treningu", "today-objective");
  section.classList.add("training-objective-section");

  const card = createCard("objective-card");
  const text = document.createElement("p");
  text.className = "objective-text";
  text.textContent = objective;

  card.append(text);
  section.append(card);
  return section;
}

function createStructureSection(
  blocks: readonly WorkoutBlockPresentation[],
): HTMLElement {
  const section = createSection("Struktura treningu", "workout-structure");
  section.classList.add("workout-structure-section");

  const card = createCard("structure-card");
  const list = document.createElement("ol");
  list.className = "workout-block-list";

  blocks.forEach((block, index) => {
    const item = document.createElement("li");
    item.className = "workout-block-item";

    const blockHeader = document.createElement("div");
    blockHeader.className = "workout-block__header";

    const name = document.createElement("strong");
    name.className = "workout-block__name";
    name.textContent = `${index + 1}. ${block.name}`;

    const tags = document.createElement("div");
    tags.className = "workout-block__tags";

    const dur = document.createElement("span");
    dur.className = "workout-tag workout-tag--duration";
    dur.textContent = block.durationText;

    const intens = document.createElement("span");
    intens.className = "workout-tag workout-tag--intensity";
    intens.textContent = block.intensityText;

    tags.append(dur, intens);
    blockHeader.append(name, tags);

    const desc = document.createElement("p");
    desc.className = "workout-block__description";
    desc.textContent = block.description;

    item.append(blockHeader, desc);
    list.append(item);

    if (index < blocks.length - 1) {
      const connector = document.createElement("div");
      connector.className = "workout-block__connector";
      connector.setAttribute("aria-hidden", "true");
      connector.textContent = "↓";
      list.append(connector);
    }
  });

  card.append(list);
  section.append(card);
  return section;
}

function createNotesSection(notes: readonly string[]): HTMLElement {
  const section = createSection("Wskazówki wykonania", "training-notes");
  section.classList.add("training-notes-section");

  const card = createCard("notes-card");
  const list = document.createElement("ul");
  list.className = "notes-list";

  for (const note of notes) {
    const item = document.createElement("li");
    item.className = "note-item";

    const checkIcon = createIcon("check");
    checkIcon.setAttribute("aria-hidden", "true");
    checkIcon.classList.add("note-icon");

    const text = document.createElement("span");
    text.textContent = note;

    item.append(checkIcon, text);
    list.append(item);
  }

  card.append(list);
  section.append(card);
  return section;
}

function createExpectedOutcomeSection(outcome: string): HTMLElement {
  const section = createSection("Spodziewany efekt i odczucia", "expected-outcome");
  section.classList.add("expected-outcome-section");

  const card = createCard("outcome-card");
  const p = document.createElement("p");
  p.className = "outcome-text";
  p.textContent = outcome;

  card.append(p);
  section.append(card);
  return section;
}

function createTechnicalDetailsSection(
  tech: TechnicalDetailsPresentation,
): HTMLElement {
  const section = createSection("Szczegóły techniczne", "technical-details");
  section.classList.add("technical-details-section");

  const card = createCard("technical-card");
  const dl = document.createElement("dl");
  dl.className = "technical-grid";

  const metrics: { label: string; value: string | null }[] = [
    { label: "Intensity Factor (IF)", value: tech.intensityFactor },
    { label: "Training Stress Score (TSS)", value: tech.tss },
    { label: "Moc znormalizowana (NP)", value: tech.np },
    { label: "Czas trwania", value: tech.duration },
    { label: "Szacowany wydatek energii", value: tech.estimatedEnergy },
  ];

  for (const metric of metrics) {
    if (metric.value !== null) {
      const row = document.createElement("div");
      row.className = "technical-row";

      const dt = document.createElement("dt");
      dt.textContent = metric.label;

      const dd = document.createElement("dd");
      dd.textContent = metric.value;

      row.append(dt, dd);
      dl.append(row);
    }
  }

  card.append(dl);
  section.append(card);
  return section;
}
