import type {
  TrainingPresentation,
  TrainingPresentationHeader,
} from "./training-presentation";

export const trainingStateKinds = [
  "ready",
  "partial",
  "unavailable",
  "stale",
  "loading",
  "failure",
] as const;

export type TrainingStateKind = (typeof trainingStateKinds)[number];

export type TrainingPresentationState =
  | {
      readonly kind: "ready";
      readonly training: TrainingPresentation;
    }
  | {
      readonly kind: "partial";
      readonly training: TrainingPresentation;
      readonly message: string;
      readonly missingData: readonly string[];
    }
  | {
      readonly kind: "unavailable";
      readonly header: TrainingPresentationHeader;
      readonly message: string;
      readonly reason: string;
      readonly nextAction: string;
    }
  | {
      readonly kind: "stale";
      readonly training: TrainingPresentation;
      readonly message: string;
      readonly lastUpdatedText: string;
    }
  | {
      readonly kind: "loading";
      readonly message: string;
    }
  | {
      readonly kind: "failure";
      readonly header: TrainingPresentationHeader;
      readonly message: string;
      readonly supportingText: string;
      readonly retryLabel: string;
    };
