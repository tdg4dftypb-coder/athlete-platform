import type { BiomarkersPresentation } from "./biomarkers-presentation";

export const biomarkersStateKinds = [
  "ready",
  "partial",
  "unavailable",
  "stale",
  "loading",
  "failure",
] as const;

export type BiomarkersStateKind = (typeof biomarkersStateKinds)[number];

export type BiomarkersPresentationState =
  | {
      readonly kind: "ready";
      readonly presentation: BiomarkersPresentation;
    }
  | {
      readonly kind: "partial";
      readonly presentation: BiomarkersPresentation;
      readonly message: string;
      readonly limitations: readonly string[];
    }
  | {
      readonly kind: "unavailable";
      readonly title: string;
      readonly message: string;
      readonly reason: string;
      readonly nextAction: string;
    }
  | {
      readonly kind: "stale";
      readonly presentation: BiomarkersPresentation;
      readonly message: string;
      readonly lastUpdatedText: string;
    }
  | {
      readonly kind: "loading";
      readonly message: string;
    }
  | {
      readonly kind: "failure";
      readonly title: string;
      readonly message: string;
      readonly supportingText: string;
      readonly retryLabel: string;
    };
