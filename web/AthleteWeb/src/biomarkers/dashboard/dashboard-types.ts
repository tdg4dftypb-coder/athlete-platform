export interface BiomarkerListItem {
  canonicalCode: string;
  name: string;
  latestValue: number | null;
  unit: string;
  collectedAt: string | null;
  status: 'normal' | 'attention' | 'warning' | 'insufficient_data';
}

export type DashboardStateKind = 'loading' | 'ready' | 'empty' | 'failure';

export interface DashboardPresentationState {
  kind: DashboardStateKind;
  items: BiomarkerListItem[];
  errorMessage?: string;
}
