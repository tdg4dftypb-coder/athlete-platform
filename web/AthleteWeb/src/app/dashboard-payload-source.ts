export interface DashboardPayloadSource {
  load(): Promise<unknown>;
}

export class StaticJsonDashboardPayloadSource implements DashboardPayloadSource {
  constructor(private readonly url: string = "/data/athlete-dashboard-v1.json") {}

  async load(): Promise<unknown> {
    const response = await fetch(this.url);
    if (!response.ok) {
      throw new Error(`Failed to load dashboard payload from ${this.url}: HTTP ${response.status}`);
    }
    return (await response.json()) as unknown;
  }
}
