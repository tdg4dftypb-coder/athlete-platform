import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LaboratoryApiClient } from '../api-client';

describe('LaboratoryApiClient', () => {
  const baseUrl = 'http://localhost:8080';
  let client: LaboratoryApiClient;

  beforeEach(() => {
    client = new LaboratoryApiClient(baseUrl, 100); // 100ms timeout for testing
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('successfully fetches history with 200 OK', async () => {
    const mockHistory = {
      contract_version: '1.0',
      canonical_code: 'ferritin',
      measurements: [{ numeric_value: 50, collected_at: '2026-01-01T12:00:00Z', verification_status: 'verified' }],
    };

    vi.mocked(fetch).mockResolvedValueOnce({
      status: 200,
      json: async () => mockHistory,
    } as Response);

    const result = await client.getHistory('ferritin');

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toEqual(mockHistory);
    }
    expect(fetch).toHaveBeenCalledWith(`${baseUrl}/api/v1/biomarkers/history/ferritin`, expect.any(Object));
  });

  it('returns bad_request on 400 status code', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 400,
    } as Response);

    const result = await client.getTrend('crp');

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('bad_request');
      expect(result.error.message).toContain('Bad Request');
    }
  });

  it('returns not_found on 404 status code', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 404,
    } as Response);

    const result = await client.getInsight('glucose');

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('not_found');
      expect(result.error.message).toContain('not found');
    }
  });

  it('returns server_error on 500 status code', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 500,
    } as Response);

    const result = await client.getInsight('vitamin_d_25_oh');

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('server_error');
    }
  });

  it('returns network_error on connection failure', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const result = await client.getHistory('ferritin');

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('network_error');
    }
  });

  it('returns timeout when fetch exceeds timeout period', async () => {
    vi.mocked(fetch).mockImplementationOnce(() => {
      return new Promise((_, reject) => {
        const err = new DOMException('The user aborted a request.', 'AbortError');
        setTimeout(() => reject(err), 150);
      });
    });

    const result = await client.getTrend('ferritin');

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('timeout');
      expect(result.error.message).toContain('timed out');
    }
  });
});
