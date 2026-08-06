import { MorningBriefingApiClient } from '../api/morning-briefing-api-client';
import type { FullScreenState } from './morning-briefing-full-screen-presentation';
import { createMorningBriefingFullScreen } from './morning-briefing-full-screen-presentation';

export class MorningBriefingFullScreenContainer {
  private client: MorningBriefingApiClient;
  private mountPoint: HTMLElement;
  private onBack: () => void;

  constructor(
    mountPoint: HTMLElement,
    client: MorningBriefingApiClient,
    onBack: () => void,
  ) {
    this.mountPoint = mountPoint;
    this.client = client;
    this.onBack = onBack;
  }

  async init(): Promise<void> {
    await this.load();
  }

  private render(state: FullScreenState): void {
    const view = createMorningBriefingFullScreen(state, () => this.load(), this.onBack);
    this.mountPoint.replaceChildren(view);

    // Focus h1 after render for accessibility (consistent with app routing pattern)
    const h1 = this.mountPoint.querySelector<HTMLElement>('h1');
    h1?.focus();
  }

  async load(): Promise<void> {
    this.render({ kind: 'loading' });

    const result = await this.client.getMorningBriefing();

    if (!result.success) {
      const type = result.error.type;
      if (type === 'network_error' || type === 'timeout') {
        this.render({ kind: 'network_error', errorMessage: result.error.message });
      } else if (type === 'invalid_data') {
        this.render({ kind: 'invalid_data', errorMessage: result.error.message });
      } else {
        this.render({ kind: 'failure', errorMessage: result.error.message });
      }
      return;
    }

    const briefing = result.data;
    switch (briefing.status) {
      case 'ready':
        this.render({ kind: 'ready', briefing });
        break;
      case 'partial':
        this.render({ kind: 'partial', briefing });
        break;
      case 'unavailable':
        this.render({ kind: 'unavailable', briefing });
        break;
      case 'stale':
        this.render({ kind: 'stale', briefing });
        break;
    }
  }
}
