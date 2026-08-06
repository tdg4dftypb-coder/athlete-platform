import type {
  PerformanceHistoryEntryWire,
} from '../api/performance-lab-api-types';


export type DetailViewState =
  | { kind: 'loading' }
  | { kind: 'not_found' }
  | { kind: 'ready'; entry: PerformanceHistoryEntryWire }
  | { kind: 'failure'; message: string }
  | { kind: 'network_error' }
  | { kind: 'invalid_data' };

export function formatThresholdStatusBadge(status: string): string {
  switch (status) {
    case 'detected':
      return 'Wykryty';
    case 'not_reached':
      return 'Nieosiągnięty';
    case 'insufficient_data':
      return 'Brak danych';
    case 'invalid_curve':
      return 'Nieprawidłowa krzywa';
    default:
      return status;
  }
}
