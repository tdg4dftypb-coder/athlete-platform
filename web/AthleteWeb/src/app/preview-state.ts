import {
  morningBriefingStateKinds,
  type MorningBriefingPresentationState,
  type MorningBriefingStateKind,
} from "../models/morning-briefing-presentation-state";
import { payloadFixtures, type PayloadFixtureName } from "../fixtures/athlete-dashboard-payload-fixtures";
import { parseAndMapAthleteDashboardToMorningBriefing } from "../mappers/morning-briefing-mapper";
import type { MappingContext } from "../mappers/mapping-context";
import {
  recoveryStateKinds,
  type RecoveryPresentationState,
  type RecoveryStateKind,
} from "../models/recovery-presentation-state";
import { parseAndMapAthleteDashboardToRecovery } from "../mappers/recovery-mapper";

export function resolvePreviewState(
  search: string,
  states: Readonly<Record<MorningBriefingStateKind, MorningBriefingPresentationState>>,
): MorningBriefingPresentationState {
  const requested = new URLSearchParams(search).get("state");
  const kind = morningBriefingStateKinds.find((candidate) => candidate === requested);
  return states[kind ?? "ready"];
}

export function resolveApplicationPreviewState(
  search: string,
  states: Readonly<Record<MorningBriefingStateKind, MorningBriefingPresentationState>>,
  context: MappingContext,
): MorningBriefingPresentationState {
  const params = new URLSearchParams(search);
  if (params.has("state") || params.get("source") !== "payload") return resolvePreviewState(search, states);

  const requested = params.get("fixture");
  const fixtureName = isPayloadFixtureName(requested) ? requested : "malformed";
  return parseAndMapAthleteDashboardToMorningBriefing(payloadFixtures[fixtureName], context);
}

export function resolveRecoveryPreviewState(
  search: string,
  states: Readonly<Record<RecoveryStateKind, RecoveryPresentationState>>,
): RecoveryPresentationState {
  const requested = new URLSearchParams(search).get("state");
  const kind = recoveryStateKinds.find((candidate) => candidate === requested);
  return states[kind ?? "ready"];
}

export function resolveApplicationRecoveryState(
  search: string,
  states: Readonly<Record<RecoveryStateKind, RecoveryPresentationState>>,
  context: MappingContext,
): RecoveryPresentationState {
  const params = new URLSearchParams(search);
  if (params.has("state") || params.get("source") !== "payload") {
    return resolveRecoveryPreviewState(search, states);
  }

  const requested = params.get("fixture");
  const fixtureName = isPayloadFixtureName(requested) ? requested : "malformed";
  return parseAndMapAthleteDashboardToRecovery(payloadFixtures[fixtureName], context);
}

import {
  trainingStateKinds,
  type TrainingPresentationState,
  type TrainingStateKind,
} from "../models/training-presentation-state";
import { parseAndMapAthleteDashboardToTraining } from "../mappers/training-mapper";

export function resolveTrainingPreviewState(
  search: string,
  states: Readonly<Record<TrainingStateKind, TrainingPresentationState>>,
): TrainingPresentationState {
  const requested = new URLSearchParams(search).get("state");
  const kind = trainingStateKinds.find((candidate) => candidate === requested);
  return states[kind ?? "ready"];
}

export function resolveApplicationTrainingState(
  search: string,
  states: Readonly<Record<TrainingStateKind, TrainingPresentationState>>,
  context: MappingContext,
): TrainingPresentationState {
  const params = new URLSearchParams(search);
  if (params.has("state") || params.get("source") !== "payload") {
    return resolveTrainingPreviewState(search, states);
  }

  const requested = params.get("fixture");
  const fixtureName = isPayloadFixtureName(requested) ? requested : "malformed";
  return parseAndMapAthleteDashboardToTraining(payloadFixtures[fixtureName], context);
}

import type { ProgressPresentationState } from "../models/progress-presentation-state";
import { parseAndMapAthleteDashboardToProgress } from "../mappers/progress-mapper";

const progressKinds: readonly ProgressPresentationState["kind"][] = [
  "ready",
  "partial",
  "unavailable",
  "stale",
  "loading",
  "failure",
];

export function resolveProgressPreviewState(
  search: string,
  states: Readonly<Record<ProgressPresentationState["kind"], ProgressPresentationState>>,
): ProgressPresentationState {
  const requested = new URLSearchParams(search).get("state");
  const kind = progressKinds.find((candidate) => candidate === requested);
  return states[kind ?? "ready"];
}

export function resolveApplicationProgressState(
  search: string,
  states: Readonly<Record<ProgressPresentationState["kind"], ProgressPresentationState>>,
  context: MappingContext,
): ProgressPresentationState {
  const params = new URLSearchParams(search);
  if (params.has("state") || params.get("source") !== "payload") {
    return resolveProgressPreviewState(search, states);
  }

  const requested = params.get("fixture");
  const fixtureName = isPayloadFixtureName(requested) ? requested : "malformed";
  return parseAndMapAthleteDashboardToProgress(payloadFixtures[fixtureName], context);
}

function isPayloadFixtureName(value: string | null): value is PayloadFixtureName {
  return value !== null && Object.prototype.hasOwnProperty.call(payloadFixtures, value);
}
