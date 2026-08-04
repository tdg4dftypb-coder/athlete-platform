import type {
  NutritionPresentation,
  NutritionPresentationHeader,
} from "./nutrition-presentation";

export interface NutritionReadyState {
  readonly kind: "ready";
  readonly nutrition: NutritionPresentation;
}

export interface NutritionPartialState {
  readonly kind: "partial";
  readonly nutrition: NutritionPresentation;
  readonly missingData: readonly string[];
  readonly message: string;
}

export interface NutritionUnavailableState {
  readonly kind: "unavailable";
  readonly header: NutritionPresentationHeader;
  readonly reason: string;
  readonly message: string;
  readonly nextAction: string;
}

export interface NutritionStaleState {
  readonly kind: "stale";
  readonly nutrition: NutritionPresentation;
  readonly lastUpdatedText: string;
  readonly message: string;
}

export interface NutritionLoadingState {
  readonly kind: "loading";
  readonly message: string;
}

export interface NutritionFailureState {
  readonly kind: "failure";
  readonly header: NutritionPresentationHeader;
  readonly message: string;
  readonly supportingText: string;
  readonly retryLabel: string;
}

export type NutritionPresentationState =
  | NutritionReadyState
  | NutritionPartialState
  | NutritionUnavailableState
  | NutritionStaleState
  | NutritionLoadingState
  | NutritionFailureState;
