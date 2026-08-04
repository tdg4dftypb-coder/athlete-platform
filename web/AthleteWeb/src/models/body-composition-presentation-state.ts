import type {
  BodyCompositionHeaderPresentation,
  BodyCompositionPresentation,
} from "./body-composition-presentation";

export interface BodyCompositionReadyState {
  readonly kind: "ready";
  readonly body: BodyCompositionPresentation;
}

export interface BodyCompositionPartialState {
  readonly kind: "partial";
  readonly body: BodyCompositionPresentation;
  readonly missingData: readonly string[];
  readonly message: string;
}

export interface BodyCompositionUnavailableState {
  readonly kind: "unavailable";
  readonly header: BodyCompositionHeaderPresentation;
  readonly reason: string;
  readonly message: string;
  readonly nextAction: string;
}

export interface BodyCompositionStaleState {
  readonly kind: "stale";
  readonly body: BodyCompositionPresentation;
  readonly lastUpdatedText: string;
  readonly message: string;
}

export interface BodyCompositionLoadingState {
  readonly kind: "loading";
  readonly message: string;
}

export interface BodyCompositionFailureState {
  readonly kind: "failure";
  readonly header: BodyCompositionHeaderPresentation;
  readonly message: string;
  readonly supportingText: string;
  readonly retryLabel: string;
}

export type BodyCompositionPresentationState =
  | BodyCompositionReadyState
  | BodyCompositionPartialState
  | BodyCompositionUnavailableState
  | BodyCompositionStaleState
  | BodyCompositionLoadingState
  | BodyCompositionFailureState;
