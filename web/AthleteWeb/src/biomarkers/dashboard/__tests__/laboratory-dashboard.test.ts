import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createLaboratoryDashboard } from '../laboratory-dashboard-presentation';
import { LaboratoryDashboardContainer } from '../laboratory-dashboard-container';
import { LaboratoryApiClient } from '../../api/api-client';
import { BiomarkerHistory } from '../../api/api-types';

describe('LaboratoryDashboardPresentation', () => {
  const onBack = vi.fn();
  const onRetry = vi.fn();

  it('renders loading state with skeletons', () => {
    const view = createLaboratoryDashboard({ kind: 'loading', items: [] }, onBack, onRetry);
    
    expect(view.querySelector('.card-loading')).not.toBeNull();
    expect(view.querySelector('.biomarkers-skeleton')).not.toBeNull();
  });

  it('renders failure state with error message and retry button', () => {
    const view = createLaboratoryDashboard(
      { kind: 'failure', items: [], errorMessage: 'Server connection timeout' },
      onBack,
      onRetry
    );
    
    expect(view.querySelector('.card-failure')).not.toBeNull();
    expect(view.textContent).toContain('Server connection timeout');
    
    const retryBtn = view.querySelector('.btn-retry') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();
    
    retryBtn.click();
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders empty state when no biomarkers available', () => {
    const view = createLaboratoryDashboard({ kind: 'empty', items: [] }, onBack, onRetry);
    
    expect(view.querySelector('.card-empty')).not.toBeNull();
    expect(view.textContent).toContain('Brak danych');
  });

  it('renders ready state with list of biomarkers', () => {
    const items = [
      {
        canonicalCode: 'ferritin',
        name: 'Ferrytyna',
        latestValue: 45.5,
        unit: 'ng/mL',
        collectedAt: '01.01.2026',
        status: 'normal' as const,
      },
      {
        canonicalCode: 'crp',
        name: 'Białko CRP',
        latestValue: 12.0,
        unit: 'mg/L',
        collectedAt: '02.01.2026',
        status: 'warning' as const,
      }
    ];

    const view = createLaboratoryDashboard({ kind: 'ready', items }, onBack, onRetry);
    
    expect(view.querySelector('.card-biomarkers-list')).not.toBeNull();
    
    const listEl = view.querySelector('ul');
    expect(listEl?.getAttribute('role')).toBe('list');
    expect(listEl?.getAttribute('aria-label')).toContain('Lista biomarkerów');

    const rows = view.querySelectorAll('.biomarker-item-row');
    expect(rows.length).toBe(2);
    
    expect(rows[0].getAttribute('role')).toBe('link');
    expect(rows[0].getAttribute('tabindex')).toBe('0');
    expect(rows[0].getAttribute('aria-label')).toContain('Ferrytyna');
    expect(rows[0].getAttribute('aria-label')).toContain('W normie');

    expect(rows[0].textContent).toContain('Ferrytyna');
    expect(rows[0].textContent).toContain('45.5 ng/mL');
    expect(rows[0].textContent).toContain('01.01.2026');
    expect(rows[0].textContent).toContain('W normie');
    
    expect(rows[1].textContent).toContain('Białko CRP');
    expect(rows[1].textContent).toContain('12 mg/L');
    expect(rows[1].textContent).toContain('Ostrzeżenie');

    // Keyboard space press trigger check
    const popStatePromise = new Promise<void>((resolve) => {
      window.addEventListener('popstate', () => resolve(), { once: true });
    });
    
    const spaceEvent = new KeyboardEvent('keydown', { key: ' ' });
    rows[0].dispatchEvent(spaceEvent);
    return popStatePromise;
  });
});

describe('LaboratoryDashboardContainer', () => {
  let containerEl: HTMLElement;
  let mockApiClient: any;
  const onBack = vi.fn();

  beforeEach(() => {
    containerEl = document.createElement('div');
    mockApiClient = {
      getHistory: vi.fn(),
    };
  });

  it('transitions from loading to ready after fetching data', async () => {
    const mockHistory: BiomarkerHistory = {
      contract_version: '1.0',
      canonical_code: 'ferritin',
      measurements: [
        { numeric_value: 50.0, collected_at: '2026-01-01T12:00:00Z', verification_status: 'verified' }
      ]
    };

    mockApiClient.getHistory.mockResolvedValue({
      success: true,
      data: mockHistory
    });

    const container = new LaboratoryDashboardContainer(containerEl, mockApiClient as unknown as LaboratoryApiClient, onBack);
    await container.init();

    expect(containerEl.querySelector('.card-biomarkers-list')).not.toBeNull();
    expect(containerEl.textContent).toContain('Ferrytyna');
    expect(containerEl.textContent).toContain('50 ng/mL');
  });

  it('transitions to empty state if all results are empty', async () => {
    mockApiClient.getHistory.mockResolvedValue({
      success: true,
      data: { contract_version: '1.0', canonical_code: 'ferritin', measurements: [] }
    });

    const container = new LaboratoryDashboardContainer(containerEl, mockApiClient as unknown as LaboratoryApiClient, onBack);
    await container.init();

    expect(containerEl.querySelector('.card-empty')).not.toBeNull();
  });
});
