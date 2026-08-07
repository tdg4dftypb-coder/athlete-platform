import type { DecisionIntelligenceApiClient } from '../api/decision-intelligence-api-client';
import type { DecisionIntelligenceViewState, DecisionIntelligenceContainerCallbacks } from './decision-intelligence-types';
import { createDecisionIntelligencePresentation } from './decision-intelligence-presentation';
import { DecisionHistoryContainer } from '../history/decisionHistoryContainer';



export class DecisionIntelligenceContainer {
  private readonly rootEl: HTMLElement;
  private readonly client: DecisionIntelligenceApiClient;
  private readonly callbacks: DecisionIntelligenceContainerCallbacks;
  private state: DecisionIntelligenceViewState = { kind: 'loading' };

  constructor(
    rootEl: HTMLElement,
    client: DecisionIntelligenceApiClient,
    callbacks: DecisionIntelligenceContainerCallbacks = {}
  ) {
    this.rootEl = rootEl;
    this.client = client;
    this.callbacks = callbacks;
  }

  private historyContainer: DecisionHistoryContainer | null = null;

  async init(): Promise<void> {
    this.render();
    this.mountHistorySection();
    await Promise.allSettled([this.fetchData(), this.initHistory()]);
  }


  destroy(): void {
    if (this.historyContainer) {
      this.historyContainer.destroy();
      this.historyContainer = null;
    }
  }

  private mountHistorySection(): void {
    const historySlot = this.rootEl.querySelector<HTMLElement>('#decision-history-slot');
    if (historySlot) {
      this.historyContainer = new DecisionHistoryContainer(historySlot);
    }
  }

  private async initHistory(): Promise<void> {
    if (this.historyContainer) {
      await this.historyContainer.init();
    }
  }


  private async fetchData(): Promise<void> {
    this.state = { kind: 'loading' };
    this.render();

    const res = await this.client.getLatestRecord();

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
      if (res.data === null) {
        this.state = { kind: 'empty' };
      } else {
        this.state = { kind: 'ready', record: res.data };
      }
    }

    this.render();
  }

  private render(): void {
    this.rootEl.innerHTML = '';
    const presentation = createDecisionIntelligencePresentation(this.state, () => {
      this.fetchData();
    }, () => {
      if (this.callbacks.onBack) this.callbacks.onBack();
    });
    this.rootEl.appendChild(presentation);

    // Slot for history
    const historySlot = document.createElement('div');
    historySlot.id = 'decision-history-slot';
    this.rootEl.appendChild(historySlot);

    if (this.historyContainer) {
      this.mountHistorySection();
    }
  }
}
