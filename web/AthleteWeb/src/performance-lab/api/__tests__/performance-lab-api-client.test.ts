import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  PerformanceLabApiClient,
  validatePerformanceLabPayload,
} from '../performance-lab-api-client';

describe('validatePerformanceLabPayload', () => {
  it('validates a correct full payload with lactate test', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 'lac-001',
            performed_at: '2026-08-01T10:00:00+00:00',
            test_type: 'lactate_step_test',
            status: 'completed',
            modality: 'cycling',
            protocol_name: '3-min step',
            body_mass_kg: 75.0,
            ambient_temperature_c: 21.0,
            notes: 'Fasted',
            stages: [
              {
                stage_number: 1,
                duration_seconds: 180,
                power_watts: 150.0,
                speed_kph: null,
                heart_rate_bpm: 130,
                lactate_mmol_l: 1.5,
                cadence_rpm: 90.0,
                perceived_exertion: 3.0,
                completion_status: 'completed',
                notes: null,
              },
            ],
          },
          lactate_curve: {
            test_id: 'lac-001',
            points: [
              {
                stage_number: 1,
                power_watts: 150.0,
                speed_kph: null,
                heart_rate_bpm: 130,
                lactate_mmol_l: 1.5,
                absolute_change_mmol_l: null,
                relative_change_percent: null,
              },
            ],
          },
          threshold_analysis: {
            test_id: 'lac-001',
            lt1: {
              name: 'LT1',
              status: 'detected',
              stage_number: 1,
              power_watts: 150.0,
              speed_kph: null,
              heart_rate_bpm: 130,
              lactate_mmol_l: 1.5,
              target_lactate_mmol_l: 2.0,
              confidence: 0.6,
              method: 'fixed_2_mmol',
            },
            lt2: {
              name: 'LT2',
              status: 'not_reached',
              stage_number: null,
              power_watts: null,
              speed_kph: null,
              heart_rate_bpm: null,
              lactate_mmol_l: null,
              target_lactate_mmol_l: 4.0,
              confidence: null,
              method: 'fixed_4_mmol',
            },
          },
        },
      ],
    };

    const res = validatePerformanceLabPayload(raw);
    expect(res.valid).toBe(true);
  });

  it('validates empty history', () => {
    const res = validatePerformanceLabPayload({ entries: [] });
    expect(res.valid).toBe(true);
    if (res.valid) {
      expect(res.data.entries).toEqual([]);
    }
  });

  it('validates non-lactate session with null curve and analysis', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 'ftp-001',
            performed_at: '2026-08-05T12:00:00+00:00',
            test_type: 'ftp_test',
            status: 'completed',
            modality: 'cycling',
            protocol_name: '20-min FTP',
            body_mass_kg: null,
            ambient_temperature_c: null,
            notes: null,
            stages: [],
          },
          lactate_curve: null,
          threshold_analysis: null,
        },
      ],
    };

    const res = validatePerformanceLabPayload(raw);
    expect(res.valid).toBe(true);
  });

  it('fails on invalid root', () => {
    expect(validatePerformanceLabPayload(null).valid).toBe(false);
    expect(validatePerformanceLabPayload('string').valid).toBe(false);
    expect(validatePerformanceLabPayload({ entries: 'not array' }).valid).toBe(false);
  });

  it('validates all test_types, modalities, stage statuses, and threshold statuses', () => {
    const modalities = ['cycling', 'running', 'rowing', 'other'];
    const testTypes = ['lactate_step_test', 'cardiopulmonary_exercise_test', 'ftp_test', 'field_test'];
    const stageStatuses = ['completed', 'incomplete', 'skipped'];
    const threshStatuses = ['detected', 'insufficient_data', 'not_reached', 'invalid_curve'];

    for (const modality of modalities) {
      for (const testType of testTypes) {
        for (const stageStatus of stageStatuses) {
          for (const threshStatus of threshStatuses) {
            const raw = {
              entries: [
                {
                  session: {
                    test_id: `t-${modality}-${testType}`,
                    performed_at: '2026-08-01T10:00:00+00:00',
                    test_type: testType,
                    status: 'completed',
                    modality,
                    protocol_name: null,
                    body_mass_kg: null,
                    ambient_temperature_c: null,
                    notes: null,
                    stages: [
                      {
                        stage_number: 1,
                        duration_seconds: 180,
                        power_watts: 150.0,
                        speed_kph: 25.0,
                        heart_rate_bpm: 140,
                        lactate_mmol_l: 2.0,
                        cadence_rpm: 90.0,
                        perceived_exertion: 4.0,
                        completion_status: stageStatus,
                        notes: null,
                      },
                    ],
                  },
                  lactate_curve: null,
                  threshold_analysis: {
                    test_id: `t-${modality}-${testType}`,
                    lt1: {
                      name: 'LT1',
                      status: threshStatus,
                      stage_number: threshStatus === 'detected' ? 1 : null,
                      power_watts: threshStatus === 'detected' ? 150.0 : null,
                      speed_kph: null,
                      heart_rate_bpm: threshStatus === 'detected' ? 140 : null,
                      lactate_mmol_l: threshStatus === 'detected' ? 2.0 : null,
                      target_lactate_mmol_l: 2.0,
                      confidence: threshStatus === 'detected' ? 0.6 : null,
                      method: 'fixed_2_mmol',
                    },
                    lt2: {
                      name: 'LT2',
                      status: 'not_reached',
                      stage_number: null,
                      power_watts: null,
                      speed_kph: null,
                      heart_rate_bpm: null,
                      lactate_mmol_l: null,
                      target_lactate_mmol_l: 4.0,
                      confidence: null,
                      method: 'fixed_4_mmol',
                    },
                  },
                },
              ],
            };

            const res = validatePerformanceLabPayload(raw);
            expect(res.valid).toBe(true);
          }
        }
      }
    }
  });

  it('fails on invalid test_type enum', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 't1',
            performed_at: '2026-08-01T10:00:00',
            test_type: 'invalid_type',
            status: 'completed',
            modality: 'cycling',
            stages: [],
          },
          lactate_curve: null,
          threshold_analysis: null,
        },
      ],
    };
    expect(validatePerformanceLabPayload(raw).valid).toBe(false);
  });


  it('fails on invalid session status enum', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 't1',
            performed_at: '2026-08-01T10:00:00',
            test_type: 'ftp_test',
            status: 'unknown_status',
            modality: 'cycling',
            stages: [],
          },
        },
      ],
    };
    expect(validatePerformanceLabPayload(raw).valid).toBe(false);
  });

  it('fails on invalid threshold status enum', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 'lac-001',
            performed_at: '2026-08-01T10:00:00+00:00',
            test_type: 'lactate_step_test',
            status: 'completed',
            modality: 'cycling',
            stages: [],
          },
          lactate_curve: null,
          threshold_analysis: {
            test_id: 'lac-001',
            lt1: {
              name: 'LT1',
              status: 'unknown_thresh_status',
              target_lactate_mmol_l: 2.0,
              method: 'fixed_2_mmol',
            },
            lt2: {
              name: 'LT2',
              status: 'not_reached',
              target_lactate_mmol_l: 4.0,
              method: 'fixed_4_mmol',
            },
          },
        },
      ],
    };
    expect(validatePerformanceLabPayload(raw).valid).toBe(false);
  });

  it('fails on mismatched test_id in lactate_curve', () => {
    const raw = {
      entries: [
        {
          session: {
            test_id: 'lac-001',
            performed_at: '2026-08-01T10:00:00+00:00',
            test_type: 'lactate_step_test',
            status: 'completed',
            modality: 'cycling',
            stages: [],
          },
          lactate_curve: {
            test_id: 'different_id',
            points: [],
          },
          threshold_analysis: null,
        },
      ],
    };
    expect(validatePerformanceLabPayload(raw).valid).toBe(false);
  });
});

describe('PerformanceLabApiClient', () => {
  let client: PerformanceLabApiClient;

  beforeEach(() => {
    client = new PerformanceLabApiClient({ baseUrl: 'http://test-server' });
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllTimers();
  });

  it('returns success for 200 OK with valid payload', async () => {
    const validJson = JSON.stringify({ entries: [] });
    vi.mocked(fetch).mockResolvedValue({
      status: 200,
      ok: true,
      text: async () => validJson,
    } as Response);

    const res = await client.getHistory();
    expect(res.success).toBe(true);
    if (res.success) {
      expect(res.data.entries).toEqual([]);
    }
  });

  it('returns server_unavailable on 503 Service Unavailable', async () => {
    vi.mocked(fetch).mockResolvedValue({
      status: 503,
      ok: false,
    } as Response);

    const res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('server_unavailable');
    }
  });

  it('returns server_error on 500 status and 404 status', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 500,
      ok: false,
    } as Response);

    let res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('server_error');
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      status: 404,
      ok: false,
    } as Response);

    res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('server_error');
    }
  });


  it('returns invalid_data on non-JSON payload', async () => {
    vi.mocked(fetch).mockResolvedValue({
      status: 200,
      ok: true,
      text: async () => 'not json',
    } as Response);

    const res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('invalid_data');
    }
  });

  it('returns invalid_data on invalid schema payload', async () => {
    vi.mocked(fetch).mockResolvedValue({
      status: 200,
      ok: true,
      text: async () => JSON.stringify({ entries: 'not_an_array' }),
    } as Response);

    const res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('invalid_data');
    }
  });

  it('returns network_error on fetch failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('Failed to fetch'));

    const res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('network_error');
    }
  });

  it('returns timeout on AbortError', async () => {
    const abortErr = new Error('Aborted');
    abortErr.name = 'AbortError';
    vi.mocked(fetch).mockRejectedValue(abortErr);

    const res = await client.getHistory();
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.type).toBe('timeout');
    }
  });
});
