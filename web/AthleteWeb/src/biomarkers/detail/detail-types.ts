export interface HistoryItem {
  value: number;
  date: string;
}

export interface TrendSummary {
  direction: string;
  strength: string;
  absoluteChange: number | null;
  relativeChange: number | null;
}

export interface MedicalInsight {
  interpretation: 'unknown' | 'positive' | 'negative' | 'neutral';
  confidence: 'none' | 'low' | 'medium' | 'high';
  summary: string | null;
  reasoning: string | null;
}

export type DetailStateKind = 'loading' | 'ready' | 'partial' | 'empty' | 'failure' | 'not_found' | 'network_error';

export interface BiomarkerDetailState {
  kind: DetailStateKind;
  canonicalCode: string;
  name?: string;
  latestValue?: number | null;
  unit?: string;
  collectedAt?: string | null;
  history?: HistoryItem[];
  trend?: TrendSummary;
  insight?: MedicalInsight;
  errorMessage?: string;
}
