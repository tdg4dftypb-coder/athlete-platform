import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';

export type DecisionIntelligenceViewState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; record: DecisionAuditRecordWire }
  | { kind: 'failure'; message: string }
  | { kind: 'network_error' }
  | { kind: 'invalid_data' };

export interface DecisionIntelligenceContainerCallbacks {
  onBack?: () => void;
}
