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

export class HttpDashboardPayloadSource implements DashboardPayloadSource {
  private readonly url: string;

  constructor(customUrl?: string) {
    const envUrl = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_DASHBOARD_API_URL;
    this.url = customUrl || envUrl || "http://127.0.0.1:8000/api/v1/dashboard";
  }

  async load(): Promise<unknown> {
    const response = await fetch(this.url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to fetch dashboard payload from ${this.url}`);
    }
    return (await response.json()) as unknown;
  }
}
