import type { DecisionHistoryPayloadWire } from './decisionHistoryTypes';

import type { DecisionValidationResult } from './decision-intelligence-api-types';
import { validateDecisionAuditRecord, type DecisionIntelligenceApiError } from './decision-intelligence-api-client';

export type DecisionHistoryApiResult =
  | { success: true; data: DecisionHistoryPayloadWire }
  | { success: false; error: DecisionIntelligenceApiError };

export function parseDecisionHistoryPayloadV1(val: unknown): DecisionValidationResult<DecisionHistoryPayloadWire> {
  if (typeof val !== 'object' || val === null) {
    return { valid: false, error: 'Root payload must be an object' };
  }

  const root = val as Record<string, unknown>;
  const keys = Object.keys(root);
  if (keys.length !== 1 || keys[0] !== 'history') {
    return { valid: false, error: 'Exact root keyset must be history' };
  }

  if (typeof root.history !== 'object' || root.history === null) {
    return { valid: false, error: 'history field must be an object' };
  }

  const historyObj = root.history as Record<string, unknown>;
  const histKeys = Object.keys(historyObj).sort();
  if (histKeys.length !== 2 || histKeys[0] !== 'count' || histKeys[1] !== 'records') {
    return { valid: false, error: 'Exact history keyset must be records and count' };
  }

  if (!Array.isArray(historyObj.records)) {
    return { valid: false, error: 'records must be an array' };
  }

  if (typeof historyObj.count !== 'number' || !Number.isInteger(historyObj.count) || historyObj.count < 0) {
    return { valid: false, error: 'count must be a non-negative integer' };
  }

  if (historyObj.count !== historyObj.records.length) {
    return { valid: false, error: 'count must match records.length' };
  }

  const validatedRecords = [];
  for (let i = 0; i < historyObj.records.length; i++) {
    const rec = historyObj.records[i];
    const valRes = validateDecisionAuditRecord(rec);
    if (!valRes.valid || !valRes.data) {
      return { valid: false, error: `Invalid audit record at index ${i}: ${valRes.error}` };
    }
    validatedRecords.push(valRes.data);
  }

  return {
    valid: true,
    data: {
      records: validatedRecords,
      count: historyObj.count,
    },
  };
}

export async function fetchDecisionHistory(
  baseUrl = '/api/v1/decision-intelligence',
  timeoutMs = 8000,
  signal?: AbortSignal
): Promise<DecisionHistoryApiResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  if (signal) {
    signal.addEventListener('abort', onExternalAbort);
  }

  try {
    const response = await fetch(`${baseUrl}/history`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });

    clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', onExternalAbort);

    if (response.status === 503) {
      return {
        success: false,
        error: {
          type: 'server_unavailable',
          message: 'Usługa historii decyzji jest tymczasowo niedostępna.',
        },
      };
    }

    if (!response.ok) {
      return {
        success: false,
        error: {
          type: 'server_error',
          message: `Błąd serwera (HTTP ${response.status}).`,
        },
      };
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      return {
        success: false,
        error: {
          type: 'invalid_data',
          message: 'Błąd sparsowania odpowiedzi JSON historii.',
        },
      };
    }

    const validation = parseDecisionHistoryPayloadV1(payload);
    if (!validation.valid || !validation.data) {
      return {
        success: false,
        error: {
          type: 'invalid_data',
          message: validation.error ?? 'Nieprawidłowy kontrakt historii.',
        },
      };
    }

    return { success: true, data: validation.data };
  } catch (err: unknown) {
    clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', onExternalAbort);

    if (err instanceof Error && err.name === 'AbortError') {
      return {
        success: false,
        error: {
          type: 'timeout',
          message: 'Upłynął limit czasu żądania historii.',
        },
      };
    }
    return {
      success: false,
      error: {
        type: 'network_error',
        message: 'Błąd połączenia z serwerem historii.',
      },
    };
  }
}
