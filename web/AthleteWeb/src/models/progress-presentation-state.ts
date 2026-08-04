import type {
  ProgressPresentation,
  ProgressPresentationHeader,
} from "./progress-presentation";

export interface ProgressReadyState {
  readonly kind: "ready";
  readonly progress: ProgressPresentation;
}

export interface ProgressPartialState {
  readonly kind: "partial";
  readonly progress: ProgressPresentation;
  readonly missingData: readonly string[];
  readonly message: string;
}

export interface ProgressUnavailableState {
  readonly kind: "unavailable";
  readonly header: ProgressPresentationHeader;
  readonly reason: string;
  readonly message: string;
  readonly nextAction: string;
}

export interface ProgressStaleState {
  readonly kind: "stale";
  readonly progress: ProgressPresentation;
  readonly lastUpdatedText: string;
  readonly message: string;
}

export interface ProgressLoadingState {
  readonly kind: "loading";
  readonly message: string;
}

export interface ProgressFailureState {
  readonly kind: "failure";
  readonly header: ProgressPresentationHeader;
  readonly message: string;
  readonly supportingText: string;
  readonly retryLabel: string;
}

export type ProgressPresentationState =
  | ProgressReadyState
  | ProgressPartialState
  | ProgressUnavailableState
  | ProgressStaleState
  | ProgressLoadingState
  | ProgressFailureState;
