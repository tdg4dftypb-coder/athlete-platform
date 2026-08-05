export interface BiomarkerPresentationItem {
  readonly code: string;
  readonly name: string;
  readonly valueLabel: string;
  readonly unitLabel: string;
  readonly referenceLabel: string;
  readonly collectedAtLabel: string;
  readonly trendLabel: string;
  readonly trendDirection: string;
  readonly laboratoryFlag: string | null;
  readonly verificationLabel: string;
  readonly limitations: readonly string[];
}

export interface BiomarkerCategoryPresentationGroup {
  readonly categoryCode: string;
  readonly displayName: string;
  readonly attentionCount: number;
  readonly unresolvedCount: number;
  readonly biomarkers: readonly BiomarkerPresentationItem[];
}

export interface UnresolvedBiomarkerPresentationItem {
  readonly id: string;
  readonly name: string;
  readonly unit: string;
  readonly collectedAtLabel: string;
  readonly reason: string;
}

export interface BiomarkersPresentationSummary {
  readonly totalReports: number;
  readonly activeReports: number;
  readonly totalObservations: number;
  readonly verifiedObservations: number;
  readonly unresolvedObservations: number;
  readonly possibleDuplicates: number;
  readonly latestCollectionDate: string | null;
}

export interface BiomarkersPresentation {
  readonly title: string;
  readonly statusLabel: string;
  readonly completenessLabel: string;
  readonly latestCollectionLabel: string;
  readonly attentionCount: number;
  readonly unresolvedCount: number;
  readonly limitations: readonly string[];
  readonly summary: BiomarkersPresentationSummary;
  readonly categories: readonly BiomarkerCategoryPresentationGroup[];
  readonly unresolvedItems: readonly UnresolvedBiomarkerPresentationItem[];
}
