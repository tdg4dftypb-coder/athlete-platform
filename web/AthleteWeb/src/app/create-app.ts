import type { MorningBriefingPresentationState } from "../models/morning-briefing-presentation-state";
import { renderMorningBriefing } from "../features/morning-briefing/morning-briefing-view";
import { renderRecoveryExperience } from "../features/recovery/recovery-view";
import { renderTrainingExperience } from "../features/training/training-view";
import type { RecoveryPresentationState } from "../models/recovery-presentation-state";
import type { TrainingPresentationState } from "../models/training-presentation-state";

import { renderProgressExperience } from "../features/progress/progress-view";
import type { ProgressPresentationState } from "../models/progress-presentation-state";

export function createApp(
  state: MorningBriefingPresentationState,
  onRetry: () => void = () => undefined,
  onOpenRecovery: () => void = () => undefined,
  onOpenTraining?: () => void,
  onOpenProgress?: () => void,
): HTMLElement {
  return renderMorningBriefing(state, onRetry, onOpenRecovery, onOpenTraining, onOpenProgress);
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

export function createProgressApp(
  state: ProgressPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderProgressExperience(state, onBack, onRetry);
}

import { renderNutritionExperience } from "../features/nutrition/nutrition-view";
import type { NutritionPresentationState } from "../models/nutrition-presentation-state";

export function createNutritionApp(
  state: NutritionPresentationState,
  onBack: () => void = () => undefined,
  onRetry: () => void = () => undefined,
): HTMLElement {
  return renderNutritionExperience(state, onBack, onRetry);
}
