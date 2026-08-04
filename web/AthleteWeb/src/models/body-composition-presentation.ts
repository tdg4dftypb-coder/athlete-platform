import type { IconName } from "../components/icon";

export interface BodyCompositionHeaderPresentation {
  readonly title: string;
  readonly dateText: string;
  readonly lastUpdatedText: string;
  readonly freshnessLabel: string | null;
}

export interface BodyCompositionHeroPresentation {
  readonly headline: string;
  readonly subheading: string;
  readonly trendDirection: "down" | "stable" | "up";
  readonly trendLabel: string;
  readonly timeframeText: string;
  readonly goalStatusBadgeText: string;
  readonly goalStatusVariant: "aligned" | "neutral" | "warning";
}

export interface BodyCompositionKeyChangeItem {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly trendDirection: "down" | "stable" | "up";
  readonly valueText: string | null;
  readonly periodText: string;
  readonly qualityNote: string | null;
  readonly iconName: IconName;
}

export interface BodyCompositionTrendPoint {
  readonly label: string;
  readonly value: number;
  readonly displayValue: string;
}

export interface BodyCompositionTrendPresentation {
  readonly title: string;
  readonly description: string;
  readonly paceText: string | null;
  readonly weeklyAverageText: string | null;
  readonly points: readonly BodyCompositionTrendPoint[];
  readonly isAvailable: boolean;
  readonly unavailableMessage: string | null;
}

export interface BodyCompositionBreakdownItem {
  readonly label: string;
  readonly valueText: string;
  readonly subtext: string | null;
  readonly statusTag: string | null;
}

export interface BodyCompositionGoalAlignmentPresentation {
  readonly title: string;
  readonly statusMessage: string;
  readonly details: readonly string[];
  readonly alignmentVariant: "aligned" | "neutral" | "warning";
}

export interface BodyCompositionDataQualityPresentation {
  readonly title: string;
  readonly completenessScoreText: string | null;
  readonly limitations: readonly string[];
  readonly isComplete: boolean;
}

export interface BodyCompositionMetricItem {
  readonly label: string;
  readonly valueText: string;
  readonly description: string | null;
}

export interface BodyCompositionTechnicalPresentation {
  readonly title: string;
  readonly metrics: readonly BodyCompositionMetricItem[];
}

export interface BodyCompositionPresentation {
  readonly source: "preview" | "payload";
  readonly header: BodyCompositionHeaderPresentation;
  readonly hero: BodyCompositionHeroPresentation;
  readonly keyChanges: readonly BodyCompositionKeyChangeItem[];
  readonly trend: BodyCompositionTrendPresentation;
  readonly breakdown: readonly BodyCompositionBreakdownItem[];
  readonly goalAlignment: BodyCompositionGoalAlignmentPresentation;
  readonly dataQuality: BodyCompositionDataQualityPresentation;
  readonly placeholderNote: string | null;
  readonly technical: BodyCompositionTechnicalPresentation;
}
