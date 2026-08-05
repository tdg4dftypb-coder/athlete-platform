/**
 * TypeScript definitions for BiomarkersDashboardPayloadV1 public contract.
 */

export interface BiomarkersDashboardMetadataPayload {
  readonly status: "ready" | "partial" | "unavailable";
  readonly completeness_score: number;
  readonly limitations: readonly string[];
  readonly evidence: readonly string[];
  readonly generated_at: string;
  readonly data_as_of: string | null;
}

export interface BiomarkersDashboardSummaryPayload {
  readonly total_reports: number;
  readonly active_reports: number;
  readonly total_observations: number;
  readonly verified_observations: number;
  readonly unresolved_observations: number;
  readonly possible_duplicates: number;
  readonly latest_collection_date: string | null;
}

export interface BiomarkerSummaryPayload {
  readonly canonical_code: string;
  readonly canonical_name: string;
  readonly category: string;
  readonly latest_observation_id: string;
  readonly latest_value: number | null;
  readonly latest_text_value: string | null;
  readonly inequality_operator: string | null;
  readonly normalized_unit: string | null;
  readonly raw_unit: string;
  readonly laboratory_reference_text: string | null;
  readonly laboratory_flag: string | null;
  readonly laboratory_provided_critical_flag: string | null;
  readonly collected_at: string;
  readonly trend_direction: string;
  readonly trend_available: boolean;
  readonly observation_count: number;
  readonly verification_status: string;
  readonly data_quality: string;
  readonly limitations: readonly string[];
}

export interface BiomarkerCategorySummaryPayload {
  readonly category: string;
  readonly display_name: string;
  readonly attention_count: number;
  readonly unresolved_count: number;
  readonly limitations: readonly string[];
  readonly biomarkers: readonly BiomarkerSummaryPayload[];
}

export interface UnresolvedBiomarkerItemPayload {
  readonly observation_id: string;
  readonly raw_name: string;
  readonly raw_unit: string;
  readonly collected_at: string;
  readonly requires_review: boolean;
  readonly normalization_status: string;
  readonly safe_reason: string;
  // Privacy assertion: raw_value is omitted in public unresolved item payload!
}

export interface BiomarkersDataQualityPayload {
  readonly completeness_score: number;
  readonly has_unresolved_items: boolean;
  readonly has_possible_duplicates: boolean;
}

export interface BiomarkersDashboardPayloadV1 {
  readonly contract_version: "1.0";
  readonly as_of: string;
  readonly metadata: BiomarkersDashboardMetadataPayload;
  readonly summary: BiomarkersDashboardSummaryPayload;
  readonly categories: readonly BiomarkerCategorySummaryPayload[];
  readonly unresolved_items: readonly UnresolvedBiomarkerItemPayload[];
  readonly data_quality: BiomarkersDataQualityPayload;
}
