export interface NutritionPresentationHeader {
  readonly title: string;
  readonly dateText: string;
  readonly lastUpdatedText: string;
  readonly freshnessLabel: string | null;
}

export interface NutritionHeroPresentation {
  readonly headline: string;
  readonly subheading: string;
  readonly statusBadgeText: string;
  readonly statusVariant: "optimal" | "moderate" | "warning";
  readonly timeframeText: string;
}

export interface NutritionFocusItem {
  readonly id: string;
  readonly title: string;
  readonly status: "check" | "alert" | "info";
  readonly description: string;
  readonly highlightText: string;
  readonly tagLabel: string;
}

export interface MealTimelineItem {
  readonly id: string;
  readonly mealName: string;
  readonly timeText: string;
  readonly timingLabel: "Przed treningiem" | "Po treningu" | "Standardowy";
  readonly description: string;
  readonly targetCarbs: string;
  readonly targetProtein: string;
}

export interface NutritionHydrationPresentation {
  readonly title: string;
  readonly currentVolumeMl: number;
  readonly targetVolumeMl: number;
  readonly progressLabel: string;
  readonly statusText: string;
}

export interface NutritionCoachSummaryPresentation {
  readonly title: string;
  readonly paragraphs: readonly string[];
}

export interface NutritionMetricItem {
  readonly label: string;
  readonly valueText: string;
  readonly targetText: string | null;
  readonly description: string | null;
}

export interface NutritionTechnicalPresentation {
  readonly title: string;
  readonly metrics: readonly NutritionMetricItem[];
}

export interface NutritionPresentation {
  readonly source: "preview" | "payload";
  readonly header: NutritionPresentationHeader;
  readonly hero: NutritionHeroPresentation;
  readonly focusItems: readonly NutritionFocusItem[];
  readonly mealTimeline: readonly MealTimelineItem[];
  readonly hydration: NutritionHydrationPresentation;
  readonly coachSummary: NutritionCoachSummaryPresentation;
  readonly technical: NutritionTechnicalPresentation;
}
