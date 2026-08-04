import type { MorningBriefingPresentationState } from "../models/morning-briefing-presentation-state";
import { renderMorningBriefing } from "../features/morning-briefing/morning-briefing-view";
import { renderRecoveryExperience } from "../features/recovery/recovery-view";
import { renderTrainingExperience } from "../features/training/training-view";
import type { RecoveryPresentationState } from "../models/recovery-presentation-state";
import type { TrainingPresentationState } from "../models/training-presentation-state";

export function createApp(
  state: MorningBriefingPresentationState,
  onRetry: () => void = () => undefined,
  onOpenRecovery: () => void = () => undefined,
  onOpenTraining?: () => void,
): HTMLElement {
  return renderMorningBriefing(state, onRetry, onOpenRecovery, onOpenTraining);
}


export function createRecoveryApp(
  state: RecoveryPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderRecoveryExperience(state, onBack, onRetry);
}

export function createTrainingApp(
  state: TrainingPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderTrainingExperience(state, onBack, onRetry);
}
