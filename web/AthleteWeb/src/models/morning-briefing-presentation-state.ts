import type {
  MorningBriefingHeader,
  MorningBriefingPresentation,
} from "./morning-briefing-presentation";

export const morningBriefingStateKinds = [
  "ready",
  "partial",
  "unavailable",
  "stale",
  "loading",
  "failure",
] as const;

export type MorningBriefingStateKind = (typeof morningBriefingStateKinds)[number];

export type MorningBriefingPresentationState =
  | {
      readonly kind: "ready";
      readonly briefing: MorningBriefingPresentation;
    }
  | {
      readonly kind: "partial";
      readonly briefing: MorningBriefingPresentation;
      readonly message: string;
      readonly missingData: readonly string[];
    }
  | {
      readonly kind: "unavailable";
      readonly header: MorningBriefingHeader;
      readonly message: string;
      readonly reason: string;
      readonly nextAction: string;
    }
  | {
      readonly kind: "stale";
      readonly briefing: MorningBriefingPresentation;
      readonly message: string;
      readonly lastUpdatedText: string;
    }
  | {
      readonly kind: "loading";
      readonly message: string;
    }
  | {
      readonly kind: "failure";
      readonly header: MorningBriefingHeader;
      readonly message: string;
      readonly supportingText: string;
      readonly retryLabel: string;
    };
