import { describe, expect, it } from "vitest";

import { resolveApplicationPreviewState } from "../src/app/preview-state";
import { parseAthleteDashboardPayloadV1 } from "../src/contracts/athlete-dashboard-payload-parser";
import type { AthleteDashboardPayloadV1 } from "../src/contracts/athlete-dashboard-payload-v1";
import {
  invalidDatePayloadFixture,
  invalidEnumPayloadFixture,
  invalidTimestampPayloadFixture,
  invalidVersionPayloadFixture,
  malformedPayloadFixture,
  missingSectionPayloadFixture,
  partialPayloadFixture,
  readyPayloadFixture,
  stalePayloadFixture,
  unavailablePayloadFixture,
} from "../src/fixtures/athlete-dashboard-payload-fixtures";
import {
  mapAthleteDashboardToMorningBriefing,
  parseAndMapAthleteDashboardToMorningBriefing,
} from "../src/mappers/morning-briefing-mapper";
import type { MappingContext } from "../src/mappers/mapping-context";
import { morningBriefingPreviewStates } from "../src/preview-data/morning-briefing-preview-data";

const context: MappingContext = {
  now: new Date("2026-08-03T08:00:00+02:00"),
  staleAfterMs: 6 * 60 * 60 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

describe("AthleteDashboard payload boundary", () => {
  it("parses a valid strict payload", () => {
    expect(parseAthleteDashboardPayloadV1(readyPayloadFixture)).toEqual({
      success: true,
      data: readyPayloadFixture,
    });
  });

  it.each([
    ["unsupported version", invalidVersionPayloadFixture],
    ["missing section", missingSectionPayloadFixture],
    ["invalid enum", invalidEnumPayloadFixture],
    ["invalid date", invalidDatePayloadFixture],
    ["invalid timestamp", invalidTimestampPayloadFixture],
    ["malformed payload", malformedPayloadFixture],
  ])("rejects %s without throwing", (_label, fixture) => {
    const result = parseAthleteDashboardPayloadV1(fixture);
    expect(result.success).toBe(false);
  });

  it("rejects invalid nulls and unknown fields", () => {
    const invalidNull = clone(readyPayloadFixture) as unknown as Record<string, unknown>;
    invalidNull.valid_for_date = null;
    const unknownField = clone(readyPayloadFixture) as unknown as Record<string, unknown>;
    unknownField.future = true;

    expect(parseAthleteDashboardPayloadV1(invalidNull).success).toBe(false);
    expect(parseAthleteDashboardPayloadV1(unknownField).success).toBe(false);
  });

  it("accepts the canonical naive timestamp supported by payload v1.0", () => {
    const payload: AthleteDashboardPayloadV1 = {
      ...clone(readyPayloadFixture),
      as_of: "2026-08-03T06:30:15",
    };

    expect(parseAthleteDashboardPayloadV1(payload).success).toBe(true);
  });

  it("maps valid fixtures to deterministic presentation states", () => {
    expect(mapAthleteDashboardToMorningBriefing(readyPayloadFixture, context).kind).toBe("ready");
    expect(mapAthleteDashboardToMorningBriefing(partialPayloadFixture, context).kind).toBe("partial");
    expect(mapAthleteDashboardToMorningBriefing(unavailablePayloadFixture, context).kind).toBe("unavailable");
    expect(mapAthleteDashboardToMorningBriefing(stalePayloadFixture, context).kind).toBe("stale");
  });

  it("labels goal completeness without presenting it as goal achievement", () => {
    const result = mapAthleteDashboardToMorningBriefing(readyPayloadFixture, context);
    expect(result.kind).toBe("ready");
    if (result.kind !== "ready") return;

    expect(result.briefing.goal.progressAccessibilityLabel).toBe("Kompletność danych celu");
    expect(result.briefing.goal.progressLabel).toBe("100% danych");
  });

  it.each([
    invalidVersionPayloadFixture,
    missingSectionPayloadFixture,
    invalidEnumPayloadFixture,
    invalidDatePayloadFixture,
    invalidTimestampPayloadFixture,
    malformedPayloadFixture,
  ])("maps validation errors to failure", (fixture) => {
    expect(parseAndMapAthleteDashboardToMorningBriefing(fixture, context).kind).toBe("failure");
  });

  it("never returns loading", () => {
    const fixtures = [readyPayloadFixture, partialPayloadFixture, unavailablePayloadFixture, stalePayloadFixture];
    expect(fixtures.map((fixture) => mapAthleteDashboardToMorningBriefing(fixture, context).kind)).not.toContain("loading");
  });

  it("is deterministic for the same payload and context", () => {
    expect(mapAthleteDashboardToMorningBriefing(readyPayloadFixture, context)).toEqual(
      mapAthleteDashboardToMorningBriefing(readyPayloadFixture, context),
    );
  });

  it("lists missing supporting data without inventing conclusions", () => {
    const result = mapAthleteDashboardToMorningBriefing(partialPayloadFixture, context);
    expect(result.kind).toBe("partial");
    if (result.kind !== "partial") return;

    expect(result.missingData).toContain("Brak HRV");
    expect(result.missingData).toContain("Brak danych snu");
    expect(result.briefing.reasons).not.toContain("HRV wróciło do normy");
    expect(result.briefing.reasons).not.toContain("Sen był lepszy niż zwykle");
  });

  it("uses the configured freshness boundary without a hidden system clock", () => {
    const payload: AthleteDashboardPayloadV1 = {
      ...clone(readyPayloadFixture),
      as_of: "2026-08-03T02:00:00+02:00",
    };
    const atBoundary = mapAthleteDashboardToMorningBriefing(payload, context);
    const beyondBoundary = mapAthleteDashboardToMorningBriefing(payload, {
      ...context,
      now: new Date(context.now.getTime() + 1),
    });

    expect(atBoundary.kind).toBe("ready");
    expect(beyondBoundary.kind).toBe("stale");
  });

  it.each(["ready", "partial", "unavailable", "stale"] as const)(
    "payload fixture query selects %s",
    (kind) => {
      expect(resolveApplicationPreviewState(
        `?source=payload&fixture=${kind}`,
        morningBriefingPreviewStates,
        context,
      ).kind).toBe(kind);
    },
  );

  it("unknown payload fixture safely resolves to failure", () => {
    expect(resolveApplicationPreviewState(
      "?source=payload&fixture=future",
      morningBriefingPreviewStates,
      context,
    ).kind).toBe("failure");
  });
});

function clone(payload: AthleteDashboardPayloadV1): AthleteDashboardPayloadV1 {
  return structuredClone(payload);
}
