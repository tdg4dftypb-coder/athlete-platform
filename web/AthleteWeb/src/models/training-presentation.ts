import type { IconName } from "../components/icon";
import type { TrainingPlanVisibility } from "../training-plan-visibility/training-plan-visibility";

export type TrainingPresentationSource = "preview" | "payload";

export interface TrainingPresentationHeader {
  readonly title: string;
  readonly dateText: string;
  readonly lastUpdatedText: string;
  readonly freshnessLabel: string | null;
}

export interface TrainingHeroPresentation {
  readonly activityIcon: IconName;
  readonly title: string;
  readonly description: string;
  readonly durationText: string;
  readonly intensityText: string;
  readonly targetGoalText: string;
}

export interface WorkoutBlockPresentation {
  readonly id: string;
  readonly name: string;
  readonly durationText: string;
  readonly intensityText: string;
  readonly description: string;
}

export interface TechnicalDetailsPresentation {
  readonly intensityFactor: string | null;
  readonly tss: string | null;
  readonly np: string | null;
  readonly duration: string | null;
  readonly estimatedEnergy: string | null;
}

/** UI-ready data for Training Experience. Knows neither domain models nor Decision Engine. */
export interface TrainingPresentation {
  readonly source: TrainingPresentationSource;
  readonly header: TrainingPresentationHeader;
  readonly hero: TrainingHeroPresentation;
  readonly objective: string;
  readonly structure: readonly WorkoutBlockPresentation[];
  readonly notes: readonly string[];
  readonly expectedOutcome: string;
  readonly technicalDetails: TechnicalDetailsPresentation | null;
  readonly planVisibility?: TrainingPlanVisibility;
}
