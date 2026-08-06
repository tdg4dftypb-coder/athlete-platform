import { MorningBriefingApiClient } from '../api/morning-briefing-api-client';
import { pickTopRecommendation } from './morning-briefing-card-types';
import type { CardState } from './morning-briefing-card-types';
import { createMorningBriefingCard } from './morning-briefing-card-presentation';

export class MorningBriefingCardContainer {
  private client: MorningBriefingApiClient;
  private mountPoint: HTMLElement;
  private onOpen: () => void;

  constructor(
    mountPoint: HTMLElement,
    client: MorningBriefingApiClient,
    onOpen: () => void,
  ) {
    this.mountPoint = mountPoint;
    this.client = client;
    this.onOpen = onOpen;
  }

  async init(): Promise<void> {
    await this.load();
  }

  private render(state: CardState): void {
    const card = createMorningBriefingCard(state, () => this.load(), this.onOpen);
    this.mountPoint.replaceChildren(card);
  }

  async load(): Promise<void> {
    this.render({ kind: 'loading' });

    const result = await this.client.getMorningBriefing();

    if (!result.success) {
      const errorType = result.error.type;
      if (errorType === 'network_error') {
        this.render({ kind: 'network_error', errorMessage: result.error.message });
      } else if (errorType === 'timeout') {
        this.render({ kind: 'network_error', errorMessage: result.error.message });
      } else if (errorType === 'invalid_data') {
        this.render({ kind: 'invalid_data', errorMessage: result.error.message });
      } else {
        // server_error, server_unavailable
        this.render({ kind: 'failure', errorMessage: result.error.message });
      }
      return;
    }

    const briefing = result.data;
    const topRec = pickTopRecommendation(briefing);

    switch (briefing.status) {
      case 'ready':
        this.render({ kind: 'ready', briefing, topRec });
        break;
      case 'partial':
        this.render({ kind: 'partial', briefing, topRec });
        break;
      case 'unavailable':
        this.render({ kind: 'unavailable', briefing });
        break;
      case 'stale':
        this.render({ kind: 'stale', briefing, topRec });
        break;
    }
  }
}
