export interface BiomarkersPayloadSource {
  load(): Promise<unknown>;
}

export class HttpBiomarkersPayloadSource implements BiomarkersPayloadSource {
  private readonly endpoint: string;

  constructor(endpoint = "/api/v1/biomarkers") {
    this.endpoint = endpoint;
  }

  async load(): Promise<unknown> {
    const response = await fetch(this.endpoint, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
    }

    try {
      return await response.json();
    } catch {
      throw new Error("Failed to parse JSON response from HTTP endpoint.");
    }
  }
}
