import type { IconName } from "../components/icon";

export interface ProgressPresentationHeader {
  readonly title: string;
  readonly dateText: string;
  readonly lastUpdatedText: string;
  readonly freshnessLabel: string | null;
}

export interface ProgressHeroPresentation {
  readonly headline: string;
  readonly subheading: string;
  readonly trendDirection: "up" | "stable" | "down";
  readonly trendLabel: string;
  readonly timeframeText: string;
}

export interface ProgressImprovementItem {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly highlightText: string;
  readonly iconName: IconName;
}

export interface ProgressAreaToImproveItem {
  readonly id: string;
  readonly title: string;
  readonly guidance: string;
  readonly focusTag: string;
  readonly tone: "coaching" | "neutral";
}

export interface ProgressTrendPoint {
  readonly label: string;
  readonly value: number;
  readonly displayValue: string;
}

export interface ProgressTrendPresentation {
  readonly title: string;
  readonly description: string;
  readonly periodText: string;
  readonly points: readonly ProgressTrendPoint[];
}

export interface ProgressAISummaryPresentation {
  readonly title: string;
  readonly paragraphs: readonly string[];
}

export interface ProgressMetricItem {
  readonly label: string;
  readonly valueText: string;
  readonly changeText: string | null;
  readonly description: string | null;
}

export interface ProgressTechnicalMetricsPresentation {
  readonly title: string;
  readonly metrics: readonly ProgressMetricItem[];
}

export interface ProgressPresentation {
  readonly source: "preview" | "payload";
  readonly header: ProgressPresentationHeader;
  readonly hero: ProgressHeroPresentation;
  readonly improvements: readonly ProgressImprovementItem[];
  readonly areasToImprove: readonly ProgressAreaToImproveItem[];
  readonly trend: ProgressTrendPresentation;
  readonly aiSummary: ProgressAISummaryPresentation;
  readonly technicalMetrics: ProgressTechnicalMetricsPresentation;
}
