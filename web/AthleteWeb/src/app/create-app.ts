import type { MorningBriefingPresentationState } from "../models/morning-briefing-presentation-state";
import { renderMorningBriefing } from "../features/morning-briefing/morning-briefing-view";

export function createApp(
  state: MorningBriefingPresentationState,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderMorningBriefing(state, onRetry);
}
