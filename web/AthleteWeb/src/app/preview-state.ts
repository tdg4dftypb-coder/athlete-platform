import {
  morningBriefingStateKinds,
  type MorningBriefingPresentationState,
  type MorningBriefingStateKind,
} from "../models/morning-briefing-presentation-state";

export function resolvePreviewState(
  search: string,
  states: Readonly<Record<MorningBriefingStateKind, MorningBriefingPresentationState>>,
): MorningBriefingPresentationState {
  const requested = new URLSearchParams(search).get("state");
  const kind = morningBriefingStateKinds.find((candidate) => candidate === requested);
  return states[kind ?? "ready"];
}
