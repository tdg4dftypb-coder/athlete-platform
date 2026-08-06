export type TrendDirection = 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
export type TrendStrength = 'none' | 'weak' | 'moderate' | 'strong';
export type TrendWindow = 'all_time';

export type Interpretation = 'unknown' | 'positive' | 'negative' | 'neutral';
export type ConfidenceLevel = 'none' | 'low' | 'medium' | 'high';

export interface BiomarkerMeasurement {
  numeric_value: number;
  collected_at: string;
  verification_status: string;
}

export interface BiomarkerHistory {
  contract_version: string;
  canonical_code: string;
  measurements: BiomarkerMeasurement[];
}

export interface BiomarkerTrend {
  canonical_code: string;
  first_value: number | null;
  latest_value: number | null;
  absolute_change: number | null;
  relative_change: number | null;
  direction: TrendDirection;
  strength: TrendStrength;
  window: TrendWindow;
  observations: number;
}

export interface BiomarkerInsight {
  canonical_code: string;
  interpretation: Interpretation;
  confidence: ConfidenceLevel;
  summary: string | null;
  reasoning: string | null;
  trend: BiomarkerTrend;
}
