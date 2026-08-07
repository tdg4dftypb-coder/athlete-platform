import type { DecisionAuditRecordWire } from './decision-intelligence-api-types';

export interface DecisionHistoryPayloadWire {
  records: readonly DecisionAuditRecordWire[];
  count: number;
}

export interface DecisionHistoryApiResponseWire {
  history: DecisionHistoryPayloadWire;
}
