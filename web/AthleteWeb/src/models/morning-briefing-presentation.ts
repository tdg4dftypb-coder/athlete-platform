export interface MorningBriefingDecision {
  readonly title: string;
  readonly duration: string;
  readonly intensity: string;
}

export interface MorningBriefingGoal {
  readonly title: string;
  readonly progressAccessibilityLabel: string;
  readonly progressLabel: string;
  readonly progressValue: number;
  readonly timeline: string;
}

export interface MorningBriefingShortcut {
  readonly id: string;
  readonly label: string;
}

export interface MorningBriefingHeader {
  readonly greeting: string;
  readonly athleteName: string;
  readonly dateText: string;
  readonly timeText: string;
}

/** UI-ready data. It deliberately knows neither backend DTOs nor domain models. */
export interface MorningBriefingPresentation extends MorningBriefingHeader {
  readonly coachMessage: readonly string[];
  readonly decision: MorningBriefingDecision;
  readonly reasons: readonly string[];
  readonly changesSinceYesterday: readonly string[];
  readonly todayPlan: readonly string[];
  readonly goal: MorningBriefingGoal;
  readonly shortcuts: readonly MorningBriefingShortcut[];
}
