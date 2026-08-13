export type VisibilityAvailability = "ready" | "partial" | "unavailable";

export interface VisiblePlannedSession {
  readonly sessionId: string;
  readonly kind: "REST" | "TRAINING";
  readonly sessionType: string | null;
  readonly durationMinutes: number;
  readonly targetTss: number | null;
}

export interface VisibleReconciliationItem {
  readonly plannedSessionId: string | null;
  readonly matchStatus: string;
  readonly executionOutcome: string | null;
  readonly completionPercent: number | null;
}

export type RuntimePhaseName =
  | "plan_prescription" | "plan_horizon_continuity" | "plan_adaptation"
  | "morning_briefing" | "publication";

export interface VisibleRuntimePhase {
  readonly available: boolean;
  readonly status: string | null;
  readonly changedState: boolean | null;
  readonly codes: readonly string[];
}

export interface VisibleRuntime {
  readonly runtimeId: string;
  readonly revision: number;
  readonly targetDate: string;
  readonly status: string;
  readonly phases: Readonly<Record<RuntimePhaseName, VisibleRuntimePhase>>;
  readonly continuity: {
    readonly sourceVersion: number | null;
    readonly resultVersion: number | null;
    readonly sourceCoverageEnd: string | null;
    readonly resultCoverageEnd: string | null;
  } | null;
  readonly adaptation: {
    readonly outcome: string | null;
    readonly sourceVersion: number | null;
    readonly resultVersion: number | null;
    readonly actions: readonly string[];
    readonly reasonCodes: readonly string[];
    readonly failureCode: string | null;
  } | null;
}

export interface TrainingPlanVisibility {
  readonly availability: VisibilityAvailability;
  readonly planId: string | null;
  readonly version: number | null;
  readonly startDate: string | null;
  readonly endDate: string | null;
  readonly futureBufferDays: number | null;
  readonly sessions: readonly VisiblePlannedSession[];
  readonly prescription: {
    readonly sessionType: string | null;
    readonly durationMinutes: number | null;
    readonly disposition: string;
  } | null;
  readonly reconciliation: readonly VisibleReconciliationItem[];
  readonly runtime: VisibleRuntime | null;
  readonly limitations: readonly string[];
}

export class TrainingPlanVisibilityClient {
  async load(targetDate: string): Promise<TrainingPlanVisibility> {
    const query = new URLSearchParams({ start_date: targetDate, end_date: targetDate });
    const results = await Promise.allSettled([
      getJson("/api/v1/training-plan/latest"),
      getJson("/api/v1/training-plan/prescriptions/latest"),
      getJson(`/api/v1/activity-calendar?${query.toString()}`),
      getJson("/api/v1/production-runtime/latest"),
    ]);
    return mapVisibility(results, targetDate);
  }
}

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`GET ${url} failed with ${response.status}`);
  return response.json() as Promise<unknown>;
}

function mapVisibility(
  results: readonly PromiseSettledResult<unknown>[],
  targetDate: string,
): TrainingPlanVisibility {
  const limitations: string[] = [];
  const plan = parseResult(results[0], parsePlanEnvelope, "Training Plan", limitations);
  const prescription = parseResult(
    results[1],
    (value) => parsePrescriptionEnvelope(value, targetDate),
    "Prescription",
    limitations,
  );
  const day = parseResult(
    results[2],
    (value) => parseCalendarDay(value, targetDate),
    "Activity Calendar",
    limitations,
  );
  const runtime = parseResult(results[3], parseRuntimeEnvelope, "Production Runtime", limitations);

  const availableSources = [plan !== null, prescription !== null, day !== null, runtime !== null].filter(Boolean).length;
  return {
    availability: availableSources === 4 ? "ready" : availableSources === 0 ? "unavailable" : "partial",
    planId: plan?.planId ?? null,
    version: plan?.version ?? null,
    startDate: plan?.startDate ?? null,
    endDate: plan?.endDate ?? null,
    futureBufferDays: plan ? dayDifference(targetDate, plan.endDate) : null,
    sessions: day?.sessions ?? [],
    prescription,
    reconciliation: day?.reconciliation ?? [],
    runtime,
    limitations,
  };
}

const runtimePhaseNames: readonly RuntimePhaseName[] = [
  "plan_prescription", "plan_horizon_continuity", "plan_adaptation",
  "morning_briefing", "publication",
];

function parseRuntimeEnvelope(input: unknown): VisibleRuntime | null {
  const root = record(input, "production runtime envelope");
  if (text(root.schema_version, "schema_version") !== "1.0") throw new Error("unsupported runtime schema");
  if (root.runtime === null) return null;
  const runtime = record(root.runtime, "production runtime");
  const rawPhases = record(runtime.phases, "runtime phases");
  const phases = Object.fromEntries(runtimePhaseNames.map((name) => {
    const value = record(rawPhases[name], name);
    const available = boolean(value.available, `${name}.available`);
    return [name, {
      available,
      status: available ? text(value.status, `${name}.status`) : null,
      changedState: available ? boolean(value.changed_state, `${name}.changed_state`) : null,
      codes: available ? textArray(value.codes, `${name}.codes`) : [],
    }];
  })) as Record<RuntimePhaseName, VisibleRuntimePhase>;
  return {
    runtimeId: text(runtime.runtime_id, "runtime_id"),
    revision: integer(runtime.revision, "revision"),
    targetDate: isoDate(runtime.target_date, "target_date"),
    status: text(runtime.status, "runtime.status"),
    phases,
    continuity: parseContinuity(rawPhases.plan_horizon_continuity),
    adaptation: parseAdaptation(rawPhases.plan_adaptation),
  };
}

function parseContinuity(input: unknown): VisibleRuntime["continuity"] {
  const phase = record(input, "continuity phase");
  if (phase.available !== true || phase.continuity === undefined) return null;
  const value = record(phase.continuity, "continuity");
  return {
    sourceVersion: nullableInteger(value.source_plan_version, "source_plan_version"),
    resultVersion: nullableInteger(value.result_plan_version, "result_plan_version"),
    sourceCoverageEnd: nullableIsoDate(value.source_coverage_end, "source_coverage_end"),
    resultCoverageEnd: nullableIsoDate(value.result_coverage_end, "result_coverage_end"),
  };
}

function parseAdaptation(input: unknown): VisibleRuntime["adaptation"] {
  const phase = record(input, "adaptation phase");
  if (phase.available !== true || phase.adaptation === undefined) return null;
  const value = record(phase.adaptation, "adaptation");
  return {
    outcome: nullableText(value.outcome, "adaptation.outcome"),
    sourceVersion: nullableInteger(value.source_plan_version, "adaptation.source_plan_version"),
    resultVersion: nullableInteger(value.result_plan_version, "adaptation.result_plan_version"),
    actions: textArray(value.actions, "adaptation.actions"),
    reasonCodes: textArray(value.reason_codes, "adaptation.reason_codes"),
    failureCode: nullableText(value.failure_code, "adaptation.failure_code"),
  };
}

function parseResult<T>(
  result: PromiseSettledResult<unknown> | undefined,
  parser: (input: unknown) => T,
  label: string,
  limitations: string[],
): T | null {
  if (result?.status !== "fulfilled") {
    limitations.push(`${label} read contract is unavailable.`);
    return null;
  }
  try {
    return parser(result.value);
  } catch {
    limitations.push(`${label} payload could not be validated.`);
    return null;
  }
}

function parsePlanEnvelope(input: unknown): {
  planId: string; version: number; startDate: string; endDate: string;
} | null {
  const root = record(input, "training plan envelope");
  if (root.plan === null) return null;
  const plan = record(root.plan, "training plan");
  return {
    planId: text(plan.plan_id, "plan_id"),
    version: integer(plan.version, "version"),
    startDate: isoDate(plan.start_date, "start_date"),
    endDate: isoDate(plan.end_date, "end_date"),
  };
}

function parsePrescriptionEnvelope(input: unknown, targetDate: string): TrainingPlanVisibility["prescription"] {
  const root = record(input, "prescription envelope");
  if (root.prescription === null) return null;
  const value = record(root.prescription, "prescription");
  if (isoDate(value.date, "prescription.date") !== targetDate) return null;
  return {
    sessionType: nullableText(value.prescribed_session_type, "prescribed_session_type"),
    durationMinutes: nullableInteger(value.prescribed_duration_minutes, "prescribed_duration_minutes"),
    disposition: text(value.disposition, "disposition"),
  };
}

function parseCalendarDay(input: unknown, targetDate: string): {
  sessions: readonly VisiblePlannedSession[];
  reconciliation: readonly VisibleReconciliationItem[];
} | null {
  const root = record(input, "activity calendar");
  if (!Array.isArray(root.days)) throw new Error("activity calendar days must be an array");
  const rawDay = root.days.find((item) => record(item, "calendar day").date === targetDate);
  if (rawDay === undefined) return null;
  const day = record(rawDay, "calendar day");
  if (!Array.isArray(day.planned_sessions)) throw new Error("planned_sessions must be an array");
  const sessions: VisiblePlannedSession[] = day.planned_sessions.map((item) => {
    const session = record(item, "planned session");
    const kind = text(session.kind, "session.kind");
    if (kind !== "REST" && kind !== "TRAINING") throw new Error("unknown session kind");
    return {
      sessionId: text(session.session_id, "session_id"),
      kind: kind as "REST" | "TRAINING",
      sessionType: nullableText(session.session_type, "session_type"),
      durationMinutes: integer(session.duration_minutes, "duration_minutes"),
      targetTss: nullableNumber(session.target_tss, "target_tss"),
    };
  });
  const reconciliation = day.reconciliation === null
    ? []
    : parseReconciliation(day.reconciliation);
  return { sessions, reconciliation };
}

function parseReconciliation(input: unknown): readonly VisibleReconciliationItem[] {
  const value = record(input, "reconciliation");
  if (!Array.isArray(value.items)) throw new Error("reconciliation items must be an array");
  return value.items.map((item) => {
    const row = record(item, "reconciliation item");
    return {
      plannedSessionId: nullableText(row.planned_session_id, "planned_session_id"),
      matchStatus: text(row.match_status, "match_status"),
      executionOutcome: nullableText(row.execution_outcome, "execution_outcome"),
      completionPercent: nullableNumber(row.completion_percent, "completion_percent"),
    };
  });
}

function dayDifference(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);
}

function record(input: unknown, label: string): Record<string, unknown> {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error(`${label} must be an object`);
  return input as Record<string, unknown>;
}
function text(input: unknown, label: string): string {
  if (typeof input !== "string" || input.length === 0) throw new Error(`${label} must be text`);
  return input;
}
function nullableText(input: unknown, label: string): string | null {
  return input === null ? null : text(input, label);
}
function integer(input: unknown, label: string): number {
  if (typeof input !== "number" || !Number.isInteger(input)) throw new Error(`${label} must be an integer`);
  return input;
}
function nullableInteger(input: unknown, label: string): number | null {
  return input === null ? null : integer(input, label);
}
function nullableNumber(input: unknown, label: string): number | null {
  if (input === null) return null;
  if (typeof input !== "number" || !Number.isFinite(input)) throw new Error(`${label} must be a number`);
  return input;
}
function boolean(input: unknown, label: string): boolean {
  if (typeof input !== "boolean") throw new Error(`${label} must be a boolean`);
  return input;
}
function textArray(input: unknown, label: string): readonly string[] {
  if (!Array.isArray(input)) throw new Error(`${label} must be an array`);
  return input.map((value) => text(value, label));
}
function nullableIsoDate(input: unknown, label: string): string | null {
  return input === null ? null : isoDate(input, label);
}
function isoDate(input: unknown, label: string): string {
  const value = text(input, label);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(`${value}T00:00:00Z`))) {
    throw new Error(`${label} must be an ISO date`);
  }
  return value;
}
