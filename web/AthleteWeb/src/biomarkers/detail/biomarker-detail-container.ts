import { LaboratoryApiClient } from '../api/api-client';
import { BiomarkerDetailState, HistoryItem } from './detail-types';
import { createBiomarkerDetailView } from './biomarker-detail-presentation';

const BIOMARKER_NAMES: Record<string, string> = {
  ferritin: 'Ferrytyna',
  crp: 'Białko C-reaktywne (CRP)',
  glucose: 'Glukoza',
  tsh: 'TSH',
  vitamin_d_25_oh: 'Witamina D (25-OH)',
  hemoglobin: 'Hemoglobina',
};

export class BiomarkerDetailContainer {
  private apiClient: LaboratoryApiClient;
  private containerElement: HTMLElement;
  private canonicalCode: string;
  private onBack: () => void;

  constructor(
    containerElement: HTMLElement,
    apiClient: LaboratoryApiClient,
    canonicalCode: string,
    onBack: () => void,
  ) {
    this.containerElement = containerElement;
    this.apiClient = apiClient;
    this.canonicalCode = canonicalCode;
    this.onBack = onBack;
  }

  async init(): Promise<void> {
    await this.loadDetail();
  }

  private render(state: BiomarkerDetailState): void {
    this.containerElement.innerHTML = '';
    const view = createBiomarkerDetailView(
      state,
      this.onBack,
      () => this.loadDetail()
    );
    this.containerElement.appendChild(view);
  }

  private async loadDetail(): Promise<void> {
    this.render({ kind: 'loading', canonicalCode: this.canonicalCode });

    try {
      const [historyResult, insightResult] = await Promise.allSettled([
        this.apiClient.getHistory(this.canonicalCode),
        this.apiClient.getInsight(this.canonicalCode),
      ]);

      const name = BIOMARKER_NAMES[this.canonicalCode] || this.canonicalCode.toUpperCase();

      // 1. Process History Result
      if (historyResult.status === 'rejected') {
        this.render({
          kind: 'network_error',
          canonicalCode: this.canonicalCode,
          name,
          errorMessage: 'Błąd połączenia sieciowego. Nie można pobrać historii.',
        });
        return;
      }

      const hRes = historyResult.value;
      if (!hRes.success) {
        if (hRes.error.type === 'not_found') {
          this.render({ kind: 'not_found', canonicalCode: this.canonicalCode, name });
        } else if (hRes.error.type === 'network_error' || hRes.error.type === 'timeout') {
          this.render({
            kind: 'network_error',
            canonicalCode: this.canonicalCode,
            name,
            errorMessage: hRes.error.message,
          });
        } else {
          this.render({
            kind: 'failure',
            canonicalCode: this.canonicalCode,
            name,
            errorMessage: hRes.error.message,
          });
        }
        return;
      }

      const historyData = hRes.data;
      const measurements = historyData.measurements || [];

      if (measurements.length === 0) {
        this.render({
          kind: 'empty',
          canonicalCode: this.canonicalCode,
          name,
          unit: 'ng/mL',
        });
        return;
      }

      // Sort measurements descending
      const sortedMeasurements = [...measurements].sort(
        (a, b) => new Date(b.collected_at).getTime() - new Date(a.collected_at).getTime()
      );
      const latest = sortedMeasurements[0];
      const historyItems: HistoryItem[] = sortedMeasurements.map((m) => ({
        value: m.numeric_value,
        date: new Date(m.collected_at).toLocaleDateString('pl-PL'),
      }));

      // 2. Process Insight Result
      const iRes = insightResult.status === 'fulfilled' ? insightResult.value : null;

      if (!iRes || !iRes.success) {
        // Partial state: History OK, but Insight failed
        this.render({
          kind: 'partial',
          canonicalCode: this.canonicalCode,
          name,
          latestValue: latest.numeric_value,
          unit: 'ng/mL',
          collectedAt: new Date(latest.collected_at).toLocaleDateString('pl-PL'),
          history: historyItems,
          errorMessage: iRes ? iRes.error.message : 'Nie udało się zsynchronizować analizy medycznej.',
        });
        return;
      }

      const insightData = iRes.data;
      const trendData = insightData.trend;

      this.render({
        kind: 'ready',
        canonicalCode: this.canonicalCode,
        name,
        latestValue: latest.numeric_value,
        unit: 'ng/mL',
        collectedAt: new Date(latest.collected_at).toLocaleDateString('pl-PL'),
        history: historyItems,
        trend: {
          direction: trendData.direction,
          strength: trendData.strength,
          absoluteChange: trendData.absolute_change,
          relativeChange: trendData.relative_change,
        },
        insight: {
          interpretation: insightData.interpretation,
          confidence: insightData.confidence,
          summary: insightData.summary,
          reasoning: insightData.reasoning,
        },
      });

    } catch (err: any) {
      this.render({
        kind: 'failure',
        canonicalCode: this.canonicalCode,
        errorMessage: err?.message || 'Wystąpił nieoczekiwany błąd wczytywania danych.',
      });
    }
  }
}
