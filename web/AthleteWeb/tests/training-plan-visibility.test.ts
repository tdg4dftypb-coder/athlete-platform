import { afterEach, describe, expect, it, vi } from "vitest";

import { renderTrainingExperience } from "../src/features/training/training-view";
import { trainingPreviewStates } from "../src/preview-data/training-preview-data";
import { TrainingPlanVisibilityClient } from "../src/training-plan-visibility/training-plan-visibility";


function response(payload: unknown, ok = true): Response {
  return { ok, status: ok ? 200 : 503, json: async () => payload } as Response;
}

const plan = {
  plan: {
    plan_id: "plan-a", start_date: "2026-08-10", end_date: "2026-09-06",
    version: 4, generated_at: "2026-08-13T06:00:00Z", supersedes_plan_id: null,
    sessions: [],
  },
};
const prescription = {
  prescription: {
    date: "2026-08-13", disposition: "AS_PLANNED",
    prescribed_session_type: "ENDURANCE", prescribed_duration_minutes: 60,
  },
};
const calendar = {
  start_date: "2026-08-13", end_date: "2026-08-13", timezone: "Europe/Warsaw",
  days: [{
    date: "2026-08-13",
    planned_sessions: [
      { session_id: "plan-a:ride", kind: "TRAINING", session_type: "ENDURANCE", duration_minutes: 90, target_tss: 65 },
      { session_id: "plan-a:swim", kind: "TRAINING", session_type: "SWIM", duration_minutes: 40, target_tss: 25 },
    ],
    planned_session: null,
    activities: [],
    reconciliation: {
      items: [
        { planned_session_id: "plan-a:ride", match_status: "MATCHED", execution_outcome: "PARTIAL", completion_percent: 75 },
        { planned_session_id: null, match_status: "UNMATCHED_ACTIVITY", execution_outcome: "UNPLANNED", completion_percent: null },
      ],
    },
  }],
};
const runtime = {
  schema_version: "1.0",
  runtime: {
    runtime_id: "runtime-a", logical_execution_key: "2026-08-13:1.0", revision: 8,
    target_date: "2026-08-13", status: "completed", started_at: "2026-08-13T05:00:00Z",
    completed_at: "2026-08-13T05:01:00Z", failure_code: null, plan: null,
    phases: {
      plan_prescription: { available: true, status: "completed", changed_state: false, codes: [], artifact_ids: [] },
      plan_horizon_continuity: {
        available: true, status: "completed", changed_state: true, codes: [], artifact_ids: [],
        continuity: { artifact_status: "resolvable", source_plan_version: 3, result_plan_version: 4,
          source_coverage_end: "2026-08-09", result_coverage_end: "2026-09-06",
          target_horizon_days: null, target_date: null },
      },
      plan_adaptation: {
        available: true, status: "completed", changed_state: true, codes: [], artifact_ids: [],
        adaptation: { artifact_status: "resolvable", outcome: "APPLIED", source_plan_id: "plan-a",
          source_plan_version: 4, result_plan_id: "plan-a", result_plan_version: 5,
          actions: ["SHORTEN"], reason_codes: ["LOAD_HIGH"], failure_code: null },
      },
      morning_briefing: { available: true, status: "completed", changed_state: false, codes: [], artifact_ids: [] },
      publication: { available: true, status: "completed", changed_state: false, codes: [], artifact_ids: [] },
    },
  },
};

afterEach(() => vi.unstubAllGlobals());

describe("Training Plan visibility", () => {
  it("loads existing read-only endpoints and preserves plural session identities", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(plan))
      .mockResolvedValueOnce(response(prescription))
      .mockResolvedValueOnce(response(calendar))
      .mockResolvedValueOnce(response(runtime));
    vi.stubGlobal("fetch", fetchMock);

    const result = await new TrainingPlanVisibilityClient().load("2026-08-13");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/v1/training-plan/latest", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/v1/training-plan/prescriptions/latest", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/v1/activity-calendar?start_date=2026-08-13&end_date=2026-08-13", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/v1/production-runtime/latest", expect.any(Object));
    expect(result.planId).toBe("plan-a");
    expect(result.version).toBe(4);
    expect(result.futureBufferDays).toBe(24);
    expect(result.sessions.map((item) => item.sessionId)).toEqual(["plan-a:ride", "plan-a:swim"]);
    expect(result.reconciliation.map((item) => item.executionOutcome)).toEqual(["PARTIAL", "UNPLANNED"]);
    expect(result.runtime?.phases.plan_horizon_continuity.changedState).toBe(true);
    expect(result.runtime?.continuity).toMatchObject({ sourceVersion: 3, resultVersion: 4 });
    expect(result.runtime?.adaptation?.outcome).toBe("APPLIED");
  });

  it("degrades to partial when an auxiliary contract is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response(plan))
      .mockResolvedValueOnce(response({}, false))
      .mockResolvedValueOnce(response(calendar))
      .mockResolvedValueOnce(response(runtime)));
    const result = await new TrainingPlanVisibilityClient().load("2026-08-13");
    expect(result.availability).toBe("partial");
    expect(result.prescription).toBeNull();
    expect(result.limitations.join(" ")).toContain("Prescription read contract is unavailable");
  });

  it("degrades only runtime subsection when its endpoint fails", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response(plan))
      .mockResolvedValueOnce(response(prescription))
      .mockResolvedValueOnce(response(calendar))
      .mockResolvedValueOnce(response({}, false)));
    const result = await new TrainingPlanVisibilityClient().load("2026-08-13");
    expect(result.availability).toBe("partial");
    expect(result.planId).toBe("plan-a");
    expect(result.runtime).toBeNull();
    expect(result.limitations.join(" ")).toContain("Production Runtime read contract is unavailable");
  });

  it("accepts historical attempts with absent continuity and adaptation phases", async () => {
    const historical = structuredClone(runtime);
    if (!historical.runtime) throw new Error("fixture runtime required");
    historical.runtime.phases.plan_horizon_continuity = { available: false } as never;
    historical.runtime.phases.plan_adaptation = { available: false } as never;
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response(plan)).mockResolvedValueOnce(response(prescription))
      .mockResolvedValueOnce(response(calendar)).mockResolvedValueOnce(response(historical)));
    const result = await new TrainingPlanVisibilityClient().load("2026-08-13");
    expect(result.availability).toBe("ready");
    expect(result.runtime?.phases.plan_horizon_continuity.available).toBe(false);
    expect(result.runtime?.continuity).toBeNull();
  });

  it.each([
    ["NO_CHANGE", null, null],
    ["REJECTED", null, "invalid_revision"],
  ])("parses canonical adaptation outcome %s", async (outcome, resultVersion, failureCode) => {
    const payload = structuredClone(runtime);
    if (!payload.runtime) throw new Error("fixture runtime required");
    const adaptation = payload.runtime.phases.plan_adaptation.adaptation as {
      outcome: string; result_plan_version: number | null; failure_code: string | null;
    };
    adaptation.outcome = outcome;
    adaptation.result_plan_version = resultVersion;
    adaptation.failure_code = failureCode;
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response(plan)).mockResolvedValueOnce(response(prescription))
      .mockResolvedValueOnce(response(calendar)).mockResolvedValueOnce(response(payload)));
    const result = await new TrainingPlanVisibilityClient().load("2026-08-13");
    expect(result.runtime?.adaptation?.outcome).toBe(outcome);
    expect(result.runtime?.adaptation?.resultVersion).toBe(resultVersion);
    expect(result.runtime?.adaptation?.failureCode).toBe(failureCode);
  });

  it("renders plan facts, every same-day session, reconciliation, and canonical runtime facts", () => {
    const base = trainingPreviewStates.ready;
    if (base.kind !== "ready") throw new Error("fixture must be ready");
    const element = renderTrainingExperience({
      kind: "ready",
      training: {
        ...base.training,
        planVisibility: {
          availability: "ready", planId: "plan-a", version: 4,
          startDate: "2026-08-10", endDate: "2026-09-06", futureBufferDays: 24,
          sessions: [
            { sessionId: "plan-a:ride", kind: "TRAINING", sessionType: "ENDURANCE", durationMinutes: 90, targetTss: 65 },
            { sessionId: "plan-a:swim", kind: "TRAINING", sessionType: "SWIM", durationMinutes: 40, targetTss: 25 },
          ],
          prescription: { sessionType: "ENDURANCE", durationMinutes: 60, disposition: "AS_PLANNED" },
          reconciliation: [{ plannedSessionId: "plan-a:ride", matchStatus: "MATCHED", executionOutcome: "PARTIAL", completionPercent: 75 }],
          runtime: {
            runtimeId: "runtime-a", revision: 8, targetDate: "2026-08-13", status: "completed",
            phases: {
              plan_prescription: { available: true, status: "completed", changedState: false, codes: [] },
              plan_horizon_continuity: { available: true, status: "completed", changedState: true, codes: [] },
              plan_adaptation: { available: true, status: "completed", changedState: true, codes: [] },
              morning_briefing: { available: true, status: "completed", changedState: false, codes: [] },
              publication: { available: true, status: "completed", changedState: false, codes: [] },
            },
            continuity: { sourceVersion: 3, resultVersion: 4, sourceCoverageEnd: "2026-08-09", resultCoverageEnd: "2026-09-06" },
            adaptation: { outcome: "APPLIED", sourceVersion: 4, resultVersion: 5, actions: ["SHORTEN"], reasonCodes: [], failureCode: null },
          },
          limitations: [],
        },
      },
    });

    const section = element.querySelector(".training-plan-runtime-section");
    expect(section?.textContent).toContain("plan-a");
    expect(element.querySelectorAll(".visibility-session")).toHaveLength(2);
    expect(element.querySelector('[data-session-id="plan-a:swim"]')?.textContent).toContain("SWIM");
    expect(section?.textContent).toContain("MATCHED · PARTIAL");
    expect(section?.textContent).toContain("PLAN_HORIZON_CONTINUITYcompleted · changed: yes");
    expect(section?.textContent).toContain("v3 → v4");
    expect(section?.textContent).toContain("APPLIED");
  });
});
