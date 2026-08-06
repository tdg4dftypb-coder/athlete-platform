import { LaboratoryApiClient } from '../api/api-client';
import { BiomarkerListItem, DashboardPresentationState } from './dashboard-types';
import { createLaboratoryDashboard } from './laboratory-dashboard-presentation';

const DEFAULT_BIOMARKER_CODES = [
  'ferritin',
  'crp',
  'glucose',
  'tsh',
  'vitamin_d_25_oh',
  'hemoglobin',
];

const BIOMARKER_NAMES: Record<string, string> = {
  ferritin: 'Ferrytyna',
  crp: 'Białko C-reaktywne (CRP)',
  glucose: 'Glukoza',
  tsh: 'TSH',
  vitamin_d_25_oh: 'Witamina D (25-OH)',
  hemoglobin: 'Hemoglobina',
};

export class LaboratoryDashboardContainer {
  private apiClient: LaboratoryApiClient;
  private containerElement: HTMLElement;
  private onBack: () => void;

  constructor(
    containerElement: HTMLElement,
    apiClient: LaboratoryApiClient,
    onBack: () => void,
  ) {
    this.containerElement = containerElement;
    this.apiClient = apiClient;
    this.onBack = onBack;
  }

  async init(): Promise<void> {
    await this.loadDashboard();
  }

  private render(state: DashboardPresentationState): void {
    this.containerElement.innerHTML = '';
    const view = createLaboratoryDashboard(
      state,
      this.onBack,
      () => this.loadDashboard()
    );
    this.containerElement.appendChild(view);
  }

  private async loadDashboard(): Promise<void> {
    this.render({ kind: 'loading', items: [] });

    try {
      const promises = DEFAULT_BIOMARKER_CODES.map(async (code) => {
        const result = await this.apiClient.getHistory(code);
        return { code, result };
      });

      const responses = await Promise.all(promises);

      // Check if all requests failed with a network/server error
      const allFailed = responses.every(
        (r) => !r.result.success && (r.result.error.type === 'network_error' || r.result.error.type === 'server_error')
      );

      if (allFailed && responses.length > 0) {
        const firstError = responses[0].result.success ? '' : responses[0].result.error.message;
        this.render({
          kind: 'failure',
          items: [],
          errorMessage: firstError || 'Nie udało się pobrać danych z serwera.',
        });
        return;
      }

      const items: BiomarkerListItem[] = [];

      for (const res of responses) {
        const name = BIOMARKER_NAMES[res.code] || res.code.toUpperCase();
        if (res.result.success) {
          const history = res.result.data;
          const measurements = history.measurements || [];

          if (measurements.length > 0) {
            // Sort measurements by date descending to get the latest one
            const sorted = [...measurements].sort(
              (a, b) => new Date(b.collected_at).getTime() - new Date(a.collected_at).getTime()
            );
            const latest = sorted[0];

            // Determine dummy status for dashboard preview based on values
            let status: BiomarkerListItem['status'] = 'normal';
            if (res.code === 'crp' && latest.numeric_value > 5.0) {
              status = 'warning';
            } else if (res.code === 'ferritin' && latest.numeric_value < 15.0) {
              status = 'attention';
            }

            items.push({
              canonicalCode: res.code,
              name,
              latestValue: latest.numeric_value,
              unit: history.measurements[0]?.verification_status ? 'ng/mL' : '', // default unit placeholder if not provided
              collectedAt: new Date(latest.collected_at).toLocaleDateString('pl-PL'),
              status,
            });
          }
        }
      }

      if (items.length === 0) {
        this.render({ kind: 'empty', items: [] });
      } else {
        this.render({ kind: 'ready', items });
      }

    } catch (err: any) {
      this.render({
        kind: 'failure',
        items: [],
        errorMessage: err?.message || 'Wystąpił nieoczekiwany błąd aplikacji.',
      });
    }
  }
}
