/**
 * Sprint 7F — History Payload Source
 *
 * Fetches GET /api/v1/biomarkers/history/{canonicalCode}.
 * No retry. No cache.
 * Three outcomes: loading (implicit, caller renders it), success (resolved Promise), failure (rejected Promise).
 */

export interface HistoryPayloadSource {
  load(canonicalCode: string): Promise<unknown>;
}

export class HttpHistoryPayloadSource implements HistoryPayloadSource {
  private readonly baseUrl: string;

  constructor(baseUrl = "/api/v1/biomarkers/history") {
    this.baseUrl = baseUrl;
  }

  async load(canonicalCode: string): Promise<unknown> {
    const endpoint = `${this.baseUrl}/${encodeURIComponent(canonicalCode)}`;

    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (response.status === 404) {
      throw new HistoryNotFoundError(
        `No history found for biomarker '${canonicalCode}'.`,
      );
    }

    if (response.status === 400) {
      throw new HistoryInvalidCodeError(
        `Invalid canonical_code: '${canonicalCode}'.`,
      );
    }

    if (!response.ok) {
      throw new Error(
        `HTTP Error ${response.status}: ${response.statusText}`,
      );
    }

    try {
      return await response.json();
    } catch {
      throw new Error("Failed to parse JSON response from history endpoint.");
    }
  }
}

export class HistoryNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HistoryNotFoundError";
  }
}

export class HistoryInvalidCodeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HistoryInvalidCodeError";
  }
}
