import type { MorningBriefingPresentationState } from "../models/morning-briefing-presentation-state";
import { renderMorningBriefing } from "../features/morning-briefing/morning-briefing-view";
import { renderRecoveryExperience } from "../features/recovery/recovery-view";
import type { RecoveryPresentationState } from "../models/recovery-presentation-state";

export function createApp(
  state: MorningBriefingPresentationState,
  onRetry: () => void = () => undefined,
  onOpenRecovery: () => void = () => undefined,
): HTMLElement {
  return renderMorningBriefing(state, onRetry, onOpenRecovery);
}

export function createRecoveryApp(
  state: RecoveryPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderRecoveryExperience(state, onBack, onRetry);
}
