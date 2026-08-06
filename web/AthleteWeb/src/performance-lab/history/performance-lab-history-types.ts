import type {
  PerformanceHistoryEntryWire,
} from '../api/performance-lab-api-types';


export type HistoryViewState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; entries: PerformanceHistoryEntryWire[] }
  | { kind: 'failure'; message: string }
  | { kind: 'network_error' }
  | { kind: 'invalid_data' };

export function formatTestTypeLabel(type: string): string {
  switch (type) {
    case 'lactate_step_test':
      return 'Test stopniowany mleczanowy';
    case 'cardiopulmonary_exercise_test':
      return 'Test spiroergometryczny (CPET)';
    case 'ftp_test':
      return 'Test FTP';
    case 'field_test':
      return 'Test terenowy';
    default:
      return type;
  }
}

export function formatModalityLabel(modality: string): string {
  switch (modality) {
    case 'cycling':
      return 'Kolarstwo';
    case 'running':
      return 'Bieg';
    case 'rowing':
      return 'Wioślarstwo';
    case 'other':
      return 'Inny';
    default:
      return modality;
  }
}

export function formatSessionStatusLabel(status: string): string {
  switch (status) {
    case 'completed':
      return 'Ukończony';
    case 'planned':
      return 'Planowany';
    case 'partial':
      return 'Częściowy';
    case 'invalid':
      return 'Nieprawidłowy';
    default:
      return status;
  }
}

export function formatDateLabel(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString('pl-PL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
}
