import {
  morningBriefingStateKinds,
  type MorningBriefingPresentationState,
  type MorningBriefingStateKind,
} from "../models/morning-briefing-presentation-state";
import { payloadFixtures, type PayloadFixtureName } from "../fixtures/athlete-dashboard-payload-fixtures";
import { parseAndMapAthleteDashboardToMorningBriefing } from "../mappers/morning-briefing-mapper";
import type { MappingContext } from "../mappers/mapping-context";

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

function isPayloadFixtureName(value: string | null): value is PayloadFixtureName {
  return value !== null && Object.prototype.hasOwnProperty.call(payloadFixtures, value);
}
