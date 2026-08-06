import type { PerformanceLabApiClient } from '../api/performance-lab-api-client';
import type { HistoryViewState } from './performance-lab-history-types';
import { createPerformanceLabHistoryPresentation } from './performance-lab-history-presentation';

export interface HistoryContainerCallbacks {
  onSelectSession?: (testId: string) => void;
}

export class PerformanceLabHistoryContainer {
  private readonly rootEl: HTMLElement;
  private readonly client: PerformanceLabApiClient;
  private readonly callbacks: HistoryContainerCallbacks;
  private state: HistoryViewState = { kind: 'loading' };

  constructor(
    rootEl: HTMLElement,
    client: PerformanceLabApiClient,
    callbacks: HistoryContainerCallbacks = {}
  ) {
    this.rootEl = rootEl;
    this.client = client;
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
      const entries = res.data.entries;
      if (entries.length === 0) {
        this.state = { kind: 'empty' };
      } else {
        this.state = { kind: 'ready', entries };
      }
    }

    this.render();
  }

  private render(): void {
    this.rootEl.innerHTML = '';
    const viewEl = createPerformanceLabHistoryPresentation({
      state: this.state,
      onRetry: () => void this.fetchData(),
      onSelectSession: (testId: string) => {
        if (this.callbacks.onSelectSession) {
          this.callbacks.onSelectSession(testId);
        }
      },
    });

    this.rootEl.appendChild(viewEl);

    // Focus heading on mount for accessibility
    const heading = this.rootEl.querySelector<HTMLElement>('.pl-history__title');
    if (heading) {
      heading.focus();
    }
  }
}
