import type { PerformanceLabApiClient } from '../api/performance-lab-api-client';
import type { DetailViewState } from './performance-test-detail-types';
import { createPerformanceTestDetailPresentation } from './performance-test-detail-presentation';

export interface DetailContainerCallbacks {
  onBack?: () => void;
}

export class PerformanceTestDetailContainer {
  private readonly rootEl: HTMLElement;
  private readonly client: PerformanceLabApiClient;
  private readonly testId: string;
  private readonly callbacks: DetailContainerCallbacks;
  private state: DetailViewState = { kind: 'loading' };

  constructor(
    rootEl: HTMLElement,
    client: PerformanceLabApiClient,
    testId: string,
    callbacks: DetailContainerCallbacks = {}
  ) {
    this.rootEl = rootEl;
    this.client = client;
    this.testId = testId;
    this.callbacks = callbacks;
  }

  async init(): Promise<void> {
    this.render();
    await this.fetchData();
  }

  private async fetchData(): Promise<void> {
    this.state = { kind: 'loading' };
    this.render();

    const res = await this.client.getHistory();

    if (!res.success) {
      switch (res.error.type) {
        case 'server_unavailable':
        case 'server_error':
          this.state = { kind: 'failure', message: res.error.message };
          break;
        case 'network_error':
          this.state = { kind: 'network_error' };
          break;
        case 'timeout':
          this.state = { kind: 'failure', message: 'Upłynął limit czasu żądania.' };
          break;
        case 'invalid_data':
          this.state = { kind: 'invalid_data' };
          break;
      }
    } else {
      const match = res.data.entries.find((e) => e.session.test_id === this.testId);
      if (!match) {
        this.state = { kind: 'not_found' };
      } else {
        this.state = { kind: 'ready', entry: match };
      }
    }

    this.render();
  }

  private render(): void {
    this.rootEl.innerHTML = '';
    const viewEl = createPerformanceTestDetailPresentation({
      state: this.state,
      onBack: this.callbacks.onBack,
      onRetry: () => void this.fetchData(),
    });

    this.rootEl.appendChild(viewEl);

    const heading = this.rootEl.querySelector<HTMLElement>('.pl-detail__title');
    if (heading) {
      heading.focus();
    }
  }
}
