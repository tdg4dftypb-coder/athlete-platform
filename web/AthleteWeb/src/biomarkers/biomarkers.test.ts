import { describe, expect, it, vi } from "vitest";
import { parseBiomarkersDashboardPayloadV1 } from "./biomarkers-payload-parser";
import { HttpBiomarkersPayloadSource } from "./biomarkers-payload-source";
import {
  mapBiomarkersPayloadToPresentation,
  parseAndMapBiomarkersPayloadToPresentation,
} from "./biomarkers-mapper";
import { resolveBiomarkersPreviewState } from "../app/preview-state";
import { biomarkersPreviewStates } from "./biomarkers-preview-data";
import type { MappingContext } from "../mappers/mapping-context";
import type { BiomarkersDashboardPayloadV1 } from "./biomarkers-payload-v1";

const mockContext: MappingContext = {
  now: new Date("2026-08-05T12:00:00Z"),
  staleAfterMs: 7 * 24 * 3600 * 1000,
  athleteName: "Marcin",
  locale: "pl-PL",
  timeZone: "Europe/Warsaw",
};

const validReadyPayload: BiomarkersDashboardPayloadV1 = {
  contract_version: "1.0",
  as_of: "2026-08-05T10:00:00Z",
  metadata: {
    status: "ready",
    completeness_score: 1.0,
    limitations: [],
    evidence: [],
    generated_at: "2026-08-05T10:00:00Z",
    data_as_of: "2026-08-01T08:00:00Z",
  },
  summary: {
    total_reports: 1,
    active_reports: 1,
    total_observations: 2,
    verified_observations: 2,
    unresolved_observations: 0,
    possible_duplicates: 0,
    latest_collection_date: "2026-08-01",
  },
  categories: [
    {
      category: "iron_panel",
      display_name: "Gospodarka żelazowa",
      attention_count: 0,
      unresolved_count: 0,
      limitations: [],
      biomarkers: [
        {
          canonical_code: "ferritin",
          canonical_name: "Ferrytyna",
          category: "iron_panel",
          latest_observation_id: "obs-1",
          latest_value: 35.0,
          latest_text_value: null,
          inequality_operator: null,
          normalized_unit: "µg/L",
          raw_unit: "ng/mL",
          laboratory_reference_text: "30-200",
          laboratory_flag: null,
          laboratory_provided_critical_flag: null,
          collected_at: "2026-08-01T08:00:00Z",
          trend_direction: "stable",
          trend_available: true,
          observation_count: 2,
          verification_status: "verified",
          data_quality: "high",
          limitations: [],
        },
      ],
    },
  ],
  unresolved_items: [],
  data_quality: {
    completeness_score: 1.0,
    has_unresolved_items: false,
    has_possible_duplicates: false,
  },
};

describe("Biomarkers Payload Parser", () => {
  it("parses valid ready payload successfully", () => {
    const res = parseBiomarkersDashboardPayloadV1(validReadyPayload);
    assert(res.success === true);
  });

  it("rejects invalid contract_version", () => {
    const invalid = { ...validReadyPayload, contract_version: "2.0" };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects invalid completeness_score", () => {
    const invalid = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, completeness_score: 1.5 },
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects NaN or Infinity numbers", () => {
    const invalid = JSON.parse(JSON.stringify(validReadyPayload));
    invalid.metadata.completeness_score = NaN;
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects privacy violations (source_document_hash in payload)", () => {
    const invalid = { ...validReadyPayload, source_document_hash: "secret_hash_123" };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.issues[0].message).toContain("Privacy violation");
    }
  });

  it("rejects privacy violations (raw_value in unresolved_items)", () => {
    const invalid = {
      ...validReadyPayload,
      unresolved_items: [
        {
          observation_id: "obs-unres-1",
          raw_name: "Glukoza",
          raw_value: "90", // Forbidden!
          raw_unit: "mg/dL",
          collected_at: "2026-08-01T08:00:00Z",
          requires_review: true,
          normalization_status: "unresolved",
          safe_reason: "test",
        },
      ],
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.issues[0].message).toContain("raw_value");
    }
  });
});

describe("HttpBiomarkersPayloadSource", () => {
  it("fetches /api/v1/biomarkers with GET method", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => validReadyPayload,
    });
    vi.stubGlobal("fetch", mockFetch);

    const data = await source.load();
    expect(data).toEqual(validReadyPayload);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/biomarkers", {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    vi.unstubAllGlobals();
  });

  it("throws error on non-2xx HTTP status", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "Internal Error" }));

    await expect(source.load()).rejects.toThrow("HTTP Error 500");

    vi.unstubAllGlobals();
  });
});

describe("Biomarkers Mapper", () => {
  it("maps valid payload to ready presentation state", () => {
    const state = mapBiomarkersPayloadToPresentation(validReadyPayload, mockContext);
    expect(state.kind).toBe("ready");
    if (state.kind === "ready") {
      expect(state.presentation.summary.totalReports).toBe(1);
      expect(state.presentation.categories[0].biomarkers[0].code).toBe("ferritin");
      expect(state.presentation.categories[0].biomarkers[0].valueLabel).toBe("35");
    }
  });

  it("maps payload with unresolved items to partial state", () => {
    const partialPayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, status: "partial", limitations: ["1 unresolved item."] },
      unresolved_items: [
        {
          observation_id: "obs-u",
          raw_name: "Unresolved Test",
          raw_unit: "U/L",
          collected_at: "2026-08-01T08:00:00Z",
          requires_review: true,
          normalization_status: "unresolved",
          safe_reason: "Unknown alias",
        },
      ],
    };

    const state = mapBiomarkersPayloadToPresentation(partialPayload, mockContext);
    expect(state.kind).toBe("partial");
    if (state.kind === "partial") {
      expect(state.presentation.unresolvedCount).toBe(1);
      expect(state.presentation.unresolvedItems[0].name).toBe("Unresolved Test");
      expect(state.presentation.unresolvedItems[0]).not.toHaveProperty("raw_value");
    }
  });

  it("maps payload with stale timestamp to stale state", () => {
    const stalePayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      as_of: "2026-07-01T08:00:00Z", // 35 days old (> 7 days)
    };

    const state = mapBiomarkersPayloadToPresentation(stalePayload, mockContext);
    expect(state.kind).toBe("stale");
  });

  it("maps unavailable payload to unavailable state", () => {
    const unavPayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, status: "unavailable", limitations: ["No reports."] },
      summary: { ...validReadyPayload.summary, total_reports: 0 },
    };

    const state = mapBiomarkersPayloadToPresentation(unavPayload, mockContext);
    expect(state.kind).toBe("unavailable");
  });

  it("returns failure state for malformed payload", () => {
    const state = parseAndMapBiomarkersPayloadToPresentation({ invalid: "data" }, mockContext);
    expect(state.kind).toBe("failure");
  });
});

describe("Preview State Routing", () => {
  it("resolves preview state by query parameter", () => {
    const readyState = resolveBiomarkersPreviewState("?view=biomarkers&state=ready", biomarkersPreviewStates);
    expect(readyState.kind).toBe("ready");

    const partialState = resolveBiomarkersPreviewState("?view=biomarkers&state=partial", biomarkersPreviewStates);
    expect(partialState.kind).toBe("partial");

    const unavState = resolveBiomarkersPreviewState("?view=biomarkers&state=unavailable", biomarkersPreviewStates);
    expect(unavState.kind).toBe("unavailable");
  });
});

function assert(condition: boolean): asserts condition {
  if (!condition) throw new Error("Assertion failed");
}
