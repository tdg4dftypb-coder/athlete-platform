import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createBiomarkerDetailView } from '../biomarker-detail-presentation';
import { BiomarkerDetailContainer } from '../biomarker-detail-container';
import { LaboratoryApiClient } from '../../api/api-client';
import { BiomarkerHistory } from '../../api/api-types';

describe('BiomarkerDetailPresentation', () => {
  const onBack = vi.fn();
  const onRetry = vi.fn();

  it('renders loading state with skeletons', () => {
    const view = createBiomarkerDetailView({ kind: 'loading', canonicalCode: 'ferritin' }, onBack, onRetry);
    expect(view.querySelector('.card-loading')).not.toBeNull();
  });

  it('renders not_found state', () => {
    const view = createBiomarkerDetailView({ kind: 'not_found', canonicalCode: 'unknown' }, onBack, onRetry);
    expect(view.querySelector('.card-not-found')).not.toBeNull();
    expect(view.textContent).toContain('Biomarker nie istnieje');
  });

  it('renders failure state with retry logic', () => {
    const view = createBiomarkerDetailView(
      { kind: 'failure', canonicalCode: 'ferritin', errorMessage: 'Sync failed' },
      onBack,
      onRetry
    );
    expect(view.querySelector('.card-failure')).not.toBeNull();
    expect(view.textContent).toContain('Sync failed');

    const retryBtn = view.querySelector('.btn-retry') as HTMLButtonElement;
    retryBtn.click();
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders ready state with history and trend tables', () => {
    const state = {
      kind: 'ready' as const,
      canonicalCode: 'ferritin',
      name: 'Ferrytyna',
      latestValue: 60,
      unit: 'ng/mL',
      collectedAt: '12.02.2026',
      history: [
        { value: 60, date: '12.02.2026' },
        { value: 50, date: '01.02.2026' }
      ],
      trend: {
        direction: 'increasing',
        strength: 'moderate',
        absoluteChange: 10,
        relativeChange: 20,
      }
    };

    const view = createBiomarkerDetailView(state, onBack, onRetry);

    expect(view.querySelector('.card-summary')).not.toBeNull();
    expect(view.textContent).toContain('60 ng/mL');
    expect(view.textContent).toContain('Pobrano: 12.02.2026');

    // Trend card check
    expect(view.querySelector('.card-trend')).not.toBeNull();
    expect(view.querySelector('.trend-direction-icon')?.textContent).toBe('↑');
    expect(view.querySelector('.trend-direction')?.textContent).toBe('Rosnący');
    
    const strengthBadge = view.querySelector('.trend-strength-badge');
    expect(strengthBadge).not.toBeNull();
    expect(strengthBadge?.textContent?.trim()).toBe('Umiarkowany');
    expect(strengthBadge?.className).toContain('badge-strength-moderate');

    expect(view.querySelector('.trend-change-absolute')?.textContent).toBe('+10 ng/mL');
    expect(view.querySelector('.trend-change-relative')?.textContent).toBe('+20%');

    // History card check
    expect(view.querySelector('.card-history')).not.toBeNull();
    const tableEl = view.querySelector('table');
    expect(tableEl?.getAttribute('aria-label')).toBe('Historia pomiarów: Ferrytyna');

    const rows = view.querySelectorAll('.history-row');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('12.02.2026');
    expect(rows[0].textContent).toContain('60 ng/mL');
  });

  it('renders trend with insufficient_data properly', () => {
    const state = {
      kind: 'ready' as const,
      canonicalCode: 'crp',
      name: 'Białko CRP',
      latestValue: 2.0,
      unit: 'mg/L',
      collectedAt: '15.02.2026',
      history: [{ value: 2.0, date: '15.02.2026' }],
      trend: {
        direction: 'insufficient_data',
        strength: 'none',
        absoluteChange: null,
        relativeChange: null,
      }
    };

    const view = createBiomarkerDetailView(state, onBack, onRetry);

    expect(view.querySelector('.trend-direction-icon')?.textContent).toBe('?');
    expect(view.querySelector('.trend-direction')?.textContent).toBe('Brak danych');
    expect(view.querySelector('.trend-strength-badge')?.textContent?.trim()).toBe('Brak');
    expect(view.querySelector('.trend-change-absolute')?.textContent?.trim()).toBe('—');
    expect(view.querySelector('.trend-change-relative')?.textContent?.trim()).toBe('—');
  });

  it('renders medical insight card with positive interpretation and high confidence', () => {
    const state = {
      kind: 'ready' as const,
      canonicalCode: 'ferritin',
      name: 'Ferrytyna',
      latestValue: 60,
      unit: 'ng/mL',
      collectedAt: '12.02.2026',
      history: [{ value: 60, date: '12.02.2026' }],
      trend: { direction: 'stable', strength: 'none', absoluteChange: 0, relativeChange: 0 },
      insight: {
        interpretation: 'positive' as const,
        confidence: 'high' as const,
        summary: 'Ferrytyna rośnie prawidłowo.',
        reasoning: 'Poziom żelaza stabilizuje się.'
      }
    };

    const view = createBiomarkerDetailView(state, onBack, onRetry);

    const insightEl = view.querySelector('.card-medical-insight');
    expect(insightEl).not.toBeNull();
    expect(insightEl?.className).toContain('interpretation-positive');
    expect(insightEl?.textContent).toContain('Ferrytyna rośnie prawidłowo.');
    expect(insightEl?.textContent).toContain('Poziom żelaza stabilizuje się.');
    
    const confidenceEl = view.querySelector('.insight-confidence-badge');
    expect(confidenceEl?.textContent).toContain('Pewność: wysoka');
  });

  it('renders medical insight card with negative interpretation and low confidence', () => {
    const state = {
      kind: 'ready' as const,
      canonicalCode: 'crp',
      name: 'CRP',
      latestValue: 12.0,
      unit: 'mg/L',
      collectedAt: '15.02.2026',
      history: [{ value: 12.0, date: '15.02.2026' }],
      trend: { direction: 'increasing', strength: 'strong', absoluteChange: 6, relativeChange: 100 },
      insight: {
        interpretation: 'negative' as const,
        confidence: 'low' as const,
        summary: 'Stan zapalny rośnie.',
        reasoning: 'CRP wzrosło dwukrotnie.'
      }
    };

    const view = createBiomarkerDetailView(state, onBack, onRetry);

    const insightEl = view.querySelector('.card-medical-insight');
    expect(insightEl?.className).toContain('interpretation-negative');
    expect(view.querySelector('.insight-confidence-badge')?.textContent).toContain('Pewność: niska');
  });

  it('renders network_error state with retry button', () => {
    const state = {
      kind: 'network_error' as const,
      canonicalCode: 'ferritin',
      errorMessage: 'Network timeout error'
    };
    const view = createBiomarkerDetailView(state, onBack, onRetry);

    expect(view.querySelector('.card-network-error')).not.toBeNull();
    expect(view.textContent).toContain('Network timeout error');
    
    const retryBtn = view.querySelector('.btn-retry') as HTMLButtonElement;
    retryBtn.click();
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders empty state when history is empty', () => {
    const state = {
      kind: 'empty' as const,
      canonicalCode: 'ferritin'
    };
    const view = createBiomarkerDetailView(state, onBack, onRetry);

    expect(view.querySelector('.card-empty')).not.toBeNull();
    expect(view.textContent).toContain('Brak historii pomiarów');
  });

  it('renders partial state with history and unavailability notice', () => {
    const state = {
      kind: 'partial' as const,
      canonicalCode: 'ferritin',
      name: 'Ferrytyna',
      latestValue: 60,
      unit: 'ng/mL',
      collectedAt: '12.02.2026',
      history: [{ value: 60, date: '12.02.2026' }]
    };
    const view = createBiomarkerDetailView(state, onBack, onRetry);

    expect(view.querySelector('.card-summary')).not.toBeNull();
    expect(view.querySelector('.card-history')).not.toBeNull();
    expect(view.querySelector('.card-trend')).toBeNull();
    expect(view.querySelector('.card-medical-insight')).toBeNull();
    
    const notice = view.querySelector('.card-notice');
    expect(notice).not.toBeNull();
    expect(notice?.textContent).toContain('chwilowo niedostępne');
  });
});

describe('BiomarkerDetailContainer', () => {
  let containerEl: HTMLElement;
  let mockApiClient: any;
  const onBack = vi.fn();

  beforeEach(() => {
    containerEl = document.createElement('div');
    mockApiClient = {
      getHistory: vi.fn(),
      getInsight: vi.fn(),
    };
  });

  it('successfully aggregates history and insight into ready state', async () => {
    const mockHistory: BiomarkerHistory = {
      contract_version: '1.0',
      canonical_code: 'ferritin',
      measurements: [
        { numeric_value: 80, collected_at: '2026-03-01T12:00:00Z', verification_status: 'verified' }
      ]
    };

    const mockInsight = {
      canonical_code: 'ferritin',
      interpretation: 'neutral',
      confidence: 'medium',
      summary: 'Stabilna ferrytyna.',
      reasoning: 'Brak zmian.',
      trend: {
        canonical_code: 'ferritin',
        first_value: 80,
        latest_value: 80,
        absolute_change: 0,
        relative_change: 0,
        direction: 'stable',
        strength: 'none',
        window: 'all_time',
        observations: 1,
      }
    };

    mockApiClient.getHistory.mockResolvedValue({ success: true, data: mockHistory });
    mockApiClient.getInsight.mockResolvedValue({ success: true, data: mockInsight });

    const container = new BiomarkerDetailContainer(
      containerEl,
      mockApiClient as unknown as LaboratoryApiClient,
      'ferritin',
      onBack
    );
    await container.init();

    expect(containerEl.querySelector('.card-summary')).not.toBeNull();
    expect(containerEl.querySelector('.card-medical-insight')).not.toBeNull();
    expect(containerEl.textContent).toContain('Ferrytyna');
    expect(containerEl.textContent).toContain('Stabilna ferrytyna.');
    expect(containerEl.querySelector('.insight-confidence-badge')?.textContent).toContain('Pewność: średnia');
  });

  it('transitions to not_found state when API returns 404', async () => {
    mockApiClient.getHistory.mockResolvedValue({
      success: false,
      error: { type: 'not_found', message: 'Not found' }
    });
    mockApiClient.getInsight.mockResolvedValue({
      success: false,
      error: { type: 'not_found', message: 'Not found' }
    });

    const container = new BiomarkerDetailContainer(
      containerEl,
      mockApiClient as unknown as LaboratoryApiClient,
      'unknown',
      onBack
    );
    await container.init();

    expect(containerEl.querySelector('.card-not-found')).not.toBeNull();
  });

  it('transitions to partial state when history succeeds but insight fails', async () => {
    const mockHistory: BiomarkerHistory = {
      contract_version: '1.0',
      canonical_code: 'ferritin',
      measurements: [{ numeric_value: 80, collected_at: '2026-03-01T12:00:00Z', verification_status: 'verified' }]
    };

    mockApiClient.getHistory.mockResolvedValue({ success: true, data: mockHistory });
    mockApiClient.getInsight.mockResolvedValue({
      success: false,
      error: { type: 'server_error', message: 'Insight backend failed' }
    });

    const container = new BiomarkerDetailContainer(
      containerEl,
      mockApiClient as unknown as LaboratoryApiClient,
      'ferritin',
      onBack
    );
    await container.init();

    expect(containerEl.querySelector('.card-summary')).not.toBeNull();
    expect(containerEl.querySelector('.card-history')).not.toBeNull();
    expect(containerEl.querySelector('.card-trend')).toBeNull();
    expect(containerEl.querySelector('.card-notice')).not.toBeNull();
  });

  it('transitions to network_error state when history fetch fails due to network', async () => {
    mockApiClient.getHistory.mockResolvedValue({
      success: false,
      error: { type: 'network_error', message: 'No internet connection' }
    });
    mockApiClient.getInsight.mockResolvedValue({
      success: false,
      error: { type: 'network_error', message: 'No internet connection' }
    });

    const container = new BiomarkerDetailContainer(
      containerEl,
      mockApiClient as unknown as LaboratoryApiClient,
      'ferritin',
      onBack
    );
    await container.init();

    expect(containerEl.querySelector('.card-network-error')).not.toBeNull();
    expect(containerEl.textContent).toContain('No internet connection');
  });
});
