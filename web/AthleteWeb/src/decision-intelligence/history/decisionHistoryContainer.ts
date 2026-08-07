import type { DecisionHistoryViewState } from './decisionHistoryTypes';
import { fetchDecisionHistory } from '../api/decisionHistoryClient';
import { createDecisionHistoryPresentation } from './decisionHistoryPresentation';


export class DecisionHistoryContainer {
  private readonly rootEl: HTMLElement;
  private readonly baseUrl: string;
  private state: DecisionHistoryViewState = { kind: 'loading' };
  private abortController: AbortController | null = null;

  constructor(rootEl: HTMLElement, baseUrl = '/api/v1/decision-intelligence') {
    this.rootEl = rootEl;
    this.baseUrl = baseUrl;
  }

  async init(): Promise<void> {
    this.render();
    await this.fetchData();
  }

  destroy(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  private async fetchData(): Promise<void> {
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    this.state = { kind: 'loading' };
    this.render();

    const res = await fetchDecisionHistory(this.baseUrl, 8000, this.abortController.signal);

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
          this.state = { kind: 'failure', message: 'Upłynął limit czasu żądania historii.' };
          break;
        case 'invalid_data':
          this.state = { kind: 'invalid_data' };
          break;
      }
    } else {
      if (res.data.records.length === 0) {
        this.state = { kind: 'empty' };
      } else {
        this.state = { kind: 'ready', payload: res.data };
      }
    }

    this.render();
  }

  private render(): void {
    this.rootEl.innerHTML = '';
    const presentation = createDecisionHistoryPresentation(this.state, () => {
      this.fetchData();
    });
    this.rootEl.appendChild(presentation);
  }
}
