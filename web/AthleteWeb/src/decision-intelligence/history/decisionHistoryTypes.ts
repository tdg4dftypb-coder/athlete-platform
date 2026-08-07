import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';
import type { DecisionHistoryPayloadWire } from '../api/decisionHistoryTypes';

export type DecisionHistoryViewState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; payload: DecisionHistoryPayloadWire }
  | { kind: 'failure'; message: string }
  | { kind: 'network_error' }
  | { kind: 'invalid_data' };

export interface DecisionHistoryEntryPresentation {
  readonly decisionId: string;
  readonly generatedAt: string;
  readonly recordedAt: string;
  readonly action: string;
  readonly actionLabel: string;
  readonly severity: string;
  readonly severityLabel: string;
  readonly confidencePercent: number;

  readonly policyVersion: string;
  readonly headline: string;
  readonly summary: string;
  readonly signalCount: number;
  readonly recommendationCount: number;
  readonly record: DecisionAuditRecordWire;
}
