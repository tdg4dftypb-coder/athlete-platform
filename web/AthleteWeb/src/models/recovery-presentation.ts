export type RecoveryPresentationSource = "preview" | "payload";
export type RecoveryTone = "positive" | "caution" | "critical" | "neutral";

export interface RecoveryPresentationHeader {
  readonly title: string;
  readonly dateText: string;
  readonly lastUpdatedText: string;
  readonly freshnessLabel: string | null;
}

export interface RecoveryStatusHeroPresentation {
  readonly statusLabel: string;
  readonly narrative: string;
  readonly score: number | null;
  readonly scoreLabel: string | null;
  readonly tone: RecoveryTone;
}

export interface RecoveryFactorPresentation {
  readonly id: "hrv" | "sleep" | "resting-heart-rate" | "fatigue";
  readonly label: string;
  readonly statusLabel: string;
  readonly valueText: string | null;
  readonly contextText: string | null;
  readonly description: string;
  readonly trendText: string | null;
  readonly tone: RecoveryTone;
}

export interface RecoveryDetailPresentation {
  readonly id: "respiratory-rate" | "oxygen-saturation";
  readonly label: string;
  readonly valueText: string;
  readonly description: string;
}

/** UI-ready data. It knows neither backend domain models nor score policy. */
export interface RecoveryPresentation {
  readonly source: RecoveryPresentationSource;
  readonly header: RecoveryPresentationHeader;
  readonly hero: RecoveryStatusHeroPresentation;
  readonly factors: readonly RecoveryFactorPresentation[];
  readonly interpretation: string;
  readonly details: readonly RecoveryDetailPresentation[];
  readonly trendSummary: string | null;
}
