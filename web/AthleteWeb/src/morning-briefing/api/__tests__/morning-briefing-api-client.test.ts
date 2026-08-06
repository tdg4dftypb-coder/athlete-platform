import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MorningBriefingApiClient, validateMorningBriefingPayload } from '../morning-briefing-api-client';

const VALID_PAYLOAD = {
  generated_at: '2026-08-06T12:00:00+00:00',
  status: 'ready',
  sections: [
    {
      title: 'Recovery',
      summary: 'Good recovery.',
      metrics: [{ title: 'Recovery score', value: 85, unit: '%', status: 'good' }],
      recommendations: [
        { title: 'Proceed as planned', description: 'Recovery ok.', priority: 'low' },
      ],
    },
  ],
};

describe('validateMorningBriefingPayload', () => {
  it('returns valid for a correct full payload', () => {
    const result = validateMorningBriefingPayload(VALID_PAYLOAD);
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.data.status).toBe('ready');
      expect(result.data.generatedAt).toBe('2026-08-06T12:00:00+00:00');
      expect(result.data.sections).toHaveLength(1);
    }
  });

  it.each(['ready', 'partial', 'unavailable', 'stale'] as const)(
    'accepts status: %s',
    (status) => {
      const payload = { ...VALID_PAYLOAD, status };
      const result = validateMorningBriefingPayload(payload);
      expect(result.valid).toBe(true);
    },
  );

  it('rejects unknown status', () => {
    const payload = { ...VALID_PAYLOAD, status: 'unknown_status' };
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(false);
  });

  it('rejects missing generated_at', () => {
    const { generated_at: _, ...payload } = VALID_PAYLOAD;
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(false);
  });

  it('rejects missing sections', () => {
    const { sections: _, ...payload } = VALID_PAYLOAD;
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(false);
  });

  it('rejects invalid section (non-object)', () => {
    const payload = { ...VALID_PAYLOAD, sections: ['not-an-object'] };
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(false);
  });

  it('rejects invalid recommendation priority', () => {
    const payload = {
      ...VALID_PAYLOAD,
      sections: [
        {
          ...VALID_PAYLOAD.sections[0],
          recommendations: [{ title: 'T', description: 'D', priority: 'ultra' }],
        },
      ],
    };
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(false);
  });

  it.each(['low', 'medium', 'high', 'critical'] as const)(
    'accepts recommendation priority: %s',
    (priority) => {
      const payload = {
        ...VALID_PAYLOAD,
        sections: [
          {
            ...VALID_PAYLOAD.sections[0],
            recommendations: [{ title: 'T', description: 'D', priority }],
          },
        ],
      };
      const result = validateMorningBriefingPayload(payload);
      expect(result.valid).toBe(true);
    },
  );

  it('accepts empty sections', () => {
    const payload = { ...VALID_PAYLOAD, sections: [] };
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.data.sections).toHaveLength(0);
    }
  });

  it('maps null metric value to null', () => {
    const payload = {
      ...VALID_PAYLOAD,
      sections: [
        {
          ...VALID_PAYLOAD.sections[0],
          metrics: [{ title: 'Score', value: null, unit: '%', status: 'ok' }],
        },
      ],
    };
    const result = validateMorningBriefingPayload(payload);
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.data.sections[0].metrics[0].value).toBeNull();
    }
  });
});

describe('MorningBriefingApiClient', () => {
  const baseUrl = 'http://localhost:8000';
  let client: MorningBriefingApiClient;

  beforeEach(() => {
    client = new MorningBriefingApiClient(baseUrl, 100);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns validated data on 200 with valid payload', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 200,
      json: async () => VALID_PAYLOAD,
    } as Response);

    const result = await client.getMorningBriefing();

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.status).toBe('ready');
    }
  });

  it('returns server_unavailable on 503', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ status: 503 } as Response);

    const result = await client.getMorningBriefing();

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('server_unavailable');
    }
  });

  it('returns server_error on 500', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ status: 500 } as Response);

    const result = await client.getMorningBriefing();

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('server_error');
    }
  });

  it('returns network_error when fetch throws', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const result = await client.getMorningBriefing();

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('network_error');
    }
  });

  it('returns timeout when request is aborted', async () => {
    vi.mocked(fetch).mockImplementationOnce((_url, options) => {
      return new Promise((_resolve, reject) => {
        const signal = options?.signal as AbortSignal | undefined;
        if (signal) {
          signal.addEventListener('abort', () => {
            const err = new Error('AbortError');
            err.name = 'AbortError';
            reject(err);
          });
        }
      });
    });

    const shortClient = new MorningBriefingApiClient(baseUrl, 1);
    const result = await shortClient.getMorningBriefing();

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('timeout');
    }
  });

  it('returns invalid_data when payload fails contract validation', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 200,
      json: async () => ({ status: 'invalid_status', sections: [], generated_at: '2026-01-01' }),
    } as Response);

    const result = await client.getMorningBriefing();

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.type).toBe('invalid_data');
    }
  });
});
