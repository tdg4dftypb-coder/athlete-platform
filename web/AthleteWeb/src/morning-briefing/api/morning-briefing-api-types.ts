// ── Allowed domain values ─────────────────────────────────────────────────────

export type MorningBriefingStatus = 'ready' | 'partial' | 'unavailable' | 'stale';
export type MorningBriefingPriority = 'low' | 'medium' | 'high' | 'critical';

// ── Wire-format types (raw JSON from backend) ─────────────────────────────────

export interface RawMorningMetric {
  title: string;
  value: number | string | null;
  unit: string | null;
  status: string;
}

export interface RawMorningRecommendation {
  title: string;
  description: string;
  priority: string;
}

export interface RawMorningSection {
  title: string;
  summary: string;
  metrics: RawMorningMetric[];
  recommendations: RawMorningRecommendation[];
}

export interface RawMorningBriefing {
  generated_at: string;
  status: string;
  sections: RawMorningSection[];
}

// ── Validated domain types ────────────────────────────────────────────────────

export interface MorningMetric {
  title: string;
  value: number | string | null;
  unit: string | null;
  status: string;
}

export interface MorningRecommendation {
  title: string;
  description: string;
  priority: MorningBriefingPriority;
}

export interface MorningSection {
  title: string;
  summary: string;
  metrics: MorningMetric[];
  recommendations: MorningRecommendation[];
}

export interface MorningBriefing {
  generatedAt: string;
  status: MorningBriefingStatus;
  sections: MorningSection[];
}

// ── Validation result ─────────────────────────────────────────────────────────

export type MorningBriefingValidationResult =
  | { valid: true; data: MorningBriefing }
  | { valid: false; reason: string };
