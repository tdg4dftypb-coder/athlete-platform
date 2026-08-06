import { BiomarkerHistory, BiomarkerTrend, BiomarkerInsight } from './api-types';

export type ApiErrorType = 'bad_request' | 'not_found' | 'server_error' | 'network_error' | 'timeout';

export interface ApiError {
  type: ApiErrorType;
  message: string;
}

export type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error: ApiError };

export class LaboratoryApiClient {
  private baseUrl: string;
  private timeoutMs: number;

  constructor(baseUrl: string = '', timeoutMs: number = 5000) {
    // Trim trailing slash from baseUrl
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.timeoutMs = timeoutMs;
  }

  private async fetchWithTimeout<T>(url: string): Promise<ApiResult<T>> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(id);

      if (response.status === 200) {
        try {
          const data = await response.json();
          return { success: true, data: data as T };
        } catch {
          return {
            success: false,
            error: { type: 'server_error', message: 'Failed to parse JSON response.' },
          };
        }
      }

      if (response.status === 400) {
        return {
          success: false,
          error: { type: 'bad_request', message: 'Bad Request. Invalid parameters.' },
        };
      }

      if (response.status === 404) {
        return {
          success: false,
          error: { type: 'not_found', message: 'Resource not found.' },
        };
      }

      // Default for 500 and other unexpected status codes
      return {
        success: false,
        error: { type: 'server_error', message: `Server error with status code: ${response.status}` },
      };

    } catch (err: any) {
      clearTimeout(id);
      if (err.name === 'AbortError') {
        return {
          success: false,
          error: { type: 'timeout', message: `Request timed out after ${this.timeoutMs}ms.` },
        };
      }
      return {
        success: false,
        error: { type: 'network_error', message: 'Network connection failed.' },
      };
    }
  }

  async getHistory(canonicalCode: string): Promise<ApiResult<BiomarkerHistory>> {
    const url = `${this.baseUrl}/api/v1/biomarkers/history/${canonicalCode}`;
    return this.fetchWithTimeout<BiomarkerHistory>(url);
  }

  async getTrend(canonicalCode: string): Promise<ApiResult<BiomarkerTrend>> {
    const url = `${this.baseUrl}/api/v1/biomarkers/trends/${canonicalCode}`;
    return this.fetchWithTimeout<BiomarkerTrend>(url);
  }

  async getInsight(canonicalCode: string): Promise<ApiResult<BiomarkerInsight>> {
    const url = `${this.baseUrl}/api/v1/biomarkers/insights/${canonicalCode}`;
    return this.fetchWithTimeout<BiomarkerInsight>(url);
  }
}
