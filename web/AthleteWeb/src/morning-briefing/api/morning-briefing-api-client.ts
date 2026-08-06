import type {
  MorningBriefing,
  MorningBriefingStatus,
  MorningBriefingPriority,
  MorningBriefingValidationResult,
  MorningRecommendation,
  MorningSection,
} from './morning-briefing-api-types';


// Re-export ApiResult pattern consistent with the project
export type { MorningBriefingValidationResult };

export type MbApiErrorType = 'server_unavailable' | 'server_error' | 'network_error' | 'timeout' | 'invalid_data';

export interface MbApiError {
  type: MbApiErrorType;
  message: string;
}

export type MbApiResult =
  | { success: true; data: MorningBriefing }
  | { success: false; error: MbApiError };

// ── Validation ────────────────────────────────────────────────────────────────

const ALLOWED_STATUSES: ReadonlySet<string> = new Set(['ready', 'partial', 'unavailable', 'stale']);
const ALLOWED_PRIORITIES: ReadonlySet<string> = new Set(['low', 'medium', 'high', 'critical']);

function validateStatus(s: unknown): s is MorningBriefingStatus {
  return typeof s === 'string' && ALLOWED_STATUSES.has(s);
}

function validatePriority(p: unknown): p is MorningBriefingPriority {
  return typeof p === 'string' && ALLOWED_PRIORITIES.has(p);
}

export function validateMorningBriefingPayload(raw: unknown): MorningBriefingValidationResult {
  if (typeof raw !== 'object' || raw === null) {
    return { valid: false, reason: 'Payload is not an object.' };
  }

  const r = raw as Record<string, unknown>;

  if (typeof r['generated_at'] !== 'string' || r['generated_at'] === '') {
    return { valid: false, reason: 'Missing or invalid generated_at.' };
  }

  if (!validateStatus(r['status'])) {
    return { valid: false, reason: `Unknown status value: ${String(r['status'])}` };
  }

  if (!Array.isArray(r['sections'])) {
    return { valid: false, reason: 'sections must be an array.' };
  }

  const sections: MorningSection[] = [];

  for (const rawSection of r['sections'] as unknown[]) {
    if (typeof rawSection !== 'object' || rawSection === null) {
      return { valid: false, reason: 'Each section must be an object.' };
    }
    const s = rawSection as Record<string, unknown>;

    if (typeof s['title'] !== 'string') {
      return { valid: false, reason: 'Section title must be a string.' };
    }
    if (typeof s['summary'] !== 'string') {
      return { valid: false, reason: 'Section summary must be a string.' };
    }
    if (!Array.isArray(s['metrics'])) {
      return { valid: false, reason: 'Section metrics must be an array.' };
    }
    if (!Array.isArray(s['recommendations'])) {
      return { valid: false, reason: 'Section recommendations must be an array.' };
    }

    const recommendations: MorningRecommendation[] = [];
    for (const rawRec of s['recommendations'] as unknown[]) {
      if (typeof rawRec !== 'object' || rawRec === null) {
        return { valid: false, reason: 'Each recommendation must be an object.' };
      }
      const rec = rawRec as Record<string, unknown>;
      if (typeof rec['title'] !== 'string') {
        return { valid: false, reason: 'Recommendation title must be a string.' };
      }
      if (typeof rec['description'] !== 'string') {
        return { valid: false, reason: 'Recommendation description must be a string.' };
      }
      if (!validatePriority(rec['priority'])) {
        return { valid: false, reason: `Unknown recommendation priority: ${String(rec['priority'])}` };
      }
      recommendations.push({
        title: rec['title'] as string,
        description: rec['description'] as string,
        priority: rec['priority'] as MorningBriefingPriority,
      });
    }

    sections.push({
      title: s['title'] as string,
      summary: s['summary'] as string,
      metrics: (s['metrics'] as unknown[]).map((m) => {
        const metric = m as Record<string, unknown>;
        return {
          title: typeof metric['title'] === 'string' ? metric['title'] : '',
          value: (typeof metric['value'] === 'number' || typeof metric['value'] === 'string')
            ? metric['value']
            : null,
          unit: typeof metric['unit'] === 'string' ? metric['unit'] : null,
          status: typeof metric['status'] === 'string' ? metric['status'] : '',
        };
      }),
      recommendations,
    });
  }

  return {
    valid: true,
    data: {
      generatedAt: r['generated_at'] as string,
      status: r['status'] as MorningBriefingStatus,
      sections,
    },
  };
}

// ── API Client ────────────────────────────────────────────────────────────────

export class MorningBriefingApiClient {
  private baseUrl: string;
  private timeoutMs: number;

  constructor(baseUrl: string = '', timeoutMs: number = 5000) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.timeoutMs = timeoutMs;
  }

  async getMorningBriefing(): Promise<MbApiResult> {
    const url = `${this.baseUrl}/api/v1/morning-briefing`;
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(id);

      if (response.status === 503) {
        return {
          success: false,
          error: { type: 'server_unavailable', message: 'Morning Briefing data source is temporarily unavailable.' },
        };
      }

      if (response.status !== 200) {
        return {
          success: false,
          error: { type: 'server_error', message: `Unexpected server response: ${response.status}` },
        };
      }

      let raw: unknown;
      try {
        raw = await response.json();
      } catch {
        return {
          success: false,
          error: { type: 'server_error', message: 'Failed to parse JSON response.' },
        };
      }

      const validation = validateMorningBriefingPayload(raw);
      if (!validation.valid) {
        return {
          success: false,
          error: { type: 'invalid_data', message: `Contract validation failed: ${validation.reason}` },
        };
      }

      return { success: true, data: validation.data };

    } catch (err: unknown) {
      clearTimeout(id);
      const isAbort = err instanceof Error && err.name === 'AbortError';
      if (isAbort) {
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
}
