import type {
  RecoveryPresentation,
  RecoveryPresentationHeader,
} from "./recovery-presentation";

export const recoveryStateKinds = [
  "ready",
  "partial",
  "unavailable",
  "stale",
  "loading",
  "failure",
] as const;

export type RecoveryStateKind = (typeof recoveryStateKinds)[number];

export type RecoveryPresentationState =
  | {
      readonly kind: "ready";
      readonly recovery: RecoveryPresentation;
    }
  | {
      readonly kind: "partial";
      readonly recovery: RecoveryPresentation;
      readonly message: string;
      readonly missingData: readonly string[];
    }
  | {
      readonly kind: "unavailable";
      readonly header: RecoveryPresentationHeader;
      readonly message: string;
      readonly reason: string;
      readonly nextAction: string;
    }
  | {
      readonly kind: "stale";
      readonly recovery: RecoveryPresentation;
      readonly message: string;
      readonly lastUpdatedText: string;
    }
  | {
      readonly kind: "loading";
      readonly message: string;
    }
  | {
      readonly kind: "failure";
      readonly header: RecoveryPresentationHeader;
      readonly message: string;
      readonly supportingText: string;
      readonly retryLabel: string;
    };
