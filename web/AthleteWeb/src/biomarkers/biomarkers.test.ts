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
import { resolveApplicationView, searchForView } from "../app/view-routing";

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
          laboratory_flag: "H",
          laboratory_provided_critical_flag: null,
          collected_at: "2026-08-01T08:00:00Z",
          trend_direction: "increasing",
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

describe("Biomarkers Payload Parser (Complete Audit Matrix)", () => {
  it("parses valid ready payload successfully", () => {
    const res = parseBiomarkersDashboardPayloadV1(validReadyPayload);
    expect(res.success).toBe(true);
  });

  it("parses valid partial payload successfully", () => {
    const partial = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, status: "partial" as const },
    };
    const res = parseBiomarkersDashboardPayloadV1(partial);
    expect(res.success).toBe(true);
  });

  it("parses valid unavailable payload successfully", () => {
    const unav = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, status: "unavailable" as const },
      summary: { ...validReadyPayload.summary, total_reports: 0 },
    };
    const res = parseBiomarkersDashboardPayloadV1(unav);
    expect(res.success).toBe(true);
  });

  it("rejects invalid contract_version", () => {
    const res = parseBiomarkersDashboardPayloadV1({ ...validReadyPayload, contract_version: "2.0" });
    expect(res.success).toBe(false);
  });

  it("rejects invalid as_of timestamp", () => {
    const res = parseBiomarkersDashboardPayloadV1({ ...validReadyPayload, as_of: "not-a-date" });
    expect(res.success).toBe(false);
  });

  it("rejects invalid data_as_of timestamp", () => {
    const invalid = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, data_as_of: "invalid-date" },
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects completeness_score < 0", () => {
    const invalid = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, completeness_score: -0.1 },
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects completeness_score > 1", () => {
    const invalid = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, completeness_score: 1.5 },
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects NaN numbers", () => {
    const invalid = JSON.parse(JSON.stringify(validReadyPayload));
    invalid.metadata.completeness_score = NaN;
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects Infinity numbers", () => {
    const invalid = JSON.parse(JSON.stringify(validReadyPayload));
    invalid.categories[0].biomarkers[0].latest_value = Infinity;
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects unknown backend status", () => {
    const invalid = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, status: "unknown_status" },
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects forbidden source_document_hash", () => {
    const res = parseBiomarkersDashboardPayloadV1({ ...validReadyPayload, source_document_hash: "hash123" });
    expect(res.success).toBe(false);
  });

  it("rejects forbidden filename", () => {
    const res = parseBiomarkersDashboardPayloadV1({ ...validReadyPayload, filename: "report.pdf" });
    expect(res.success).toBe(false);
  });

  it("rejects forbidden original_filename", () => {
    const res = parseBiomarkersDashboardPayloadV1({ ...validReadyPayload, original_filename: "lab.pdf" });
    expect(res.success).toBe(false);
  });

  it("rejects raw_value in unresolved_items", () => {
    const invalid = {
      ...validReadyPayload,
      unresolved_items: [
        {
          observation_id: "obs-u",
          raw_name: "Glukoza",
          raw_value: "90", // Privacy violation!
          raw_unit: "mg/dL",
          collected_at: "2026-08-01T08:00:00Z",
          requires_review: true,
          normalization_status: "unresolved",
          safe_reason: "reason",
        },
      ],
    };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects invalid categories structure", () => {
    const invalid = { ...validReadyPayload, categories: "not-an-array" };
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects invalid trend_direction enum", () => {
    const invalid = JSON.parse(JSON.stringify(validReadyPayload));
    invalid.categories[0].biomarkers[0].trend_direction = "super_high";
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });

  it("rejects invalid verification_status enum", () => {
    const invalid = JSON.parse(JSON.stringify(validReadyPayload));
    invalid.categories[0].biomarkers[0].verification_status = "auto_accepted";
    const res = parseBiomarkersDashboardPayloadV1(invalid);
    expect(res.success).toBe(false);
  });
});

describe("HttpBiomarkersPayloadSource Audit", () => {
  it("executes single GET request and returns unknown data", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => validReadyPayload,
    });
    vi.stubGlobal("fetch", mockFetch);

    const data = await source.load();
    expect(data).toEqual(validReadyPayload);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/biomarkers", {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    vi.unstubAllGlobals();
  });

  it("throws on non-2xx HTTP status without retrying", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 404, statusText: "Not Found" });
    vi.stubGlobal("fetch", mockFetch);

    await expect(source.load()).rejects.toThrow("HTTP Error 404");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
  });

  it("throws on invalid JSON without fallback", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => {
        throw new Error("SyntaxError");
      },
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(source.load()).rejects.toThrow("Failed to parse JSON");

    vi.unstubAllGlobals();
  });

  it("throws on network failure", async () => {
    const source = new HttpBiomarkersPayloadSource("/api/v1/biomarkers");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network Error")));

    await expect(source.load()).rejects.toThrow("Network Error");

    vi.unstubAllGlobals();
  });
});

describe("Biomarkers Mapper and Temporal Semantics", () => {
  it("maps valid payload to ready presentation state", () => {
    const state = mapBiomarkersPayloadToPresentation(validReadyPayload, mockContext);
    expect(state.kind).toBe("ready");
  });

  it("maps old data_as_of with fresh as_of to ready state (NOT stale)", () => {
    const oldLabDataPayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      as_of: "2026-08-05T10:00:00Z", // Fresh response today!
      metadata: {
        ...validReadyPayload.metadata,
        data_as_of: "2026-06-01T08:00:00Z", // Lab test from 2 months ago!
      },
    };

    const state = mapBiomarkersPayloadToPresentation(oldLabDataPayload, mockContext);
    expect(state.kind).toBe("ready"); // MUST NOT be stale!
  });

  it("maps old as_of payload timestamp to stale state", () => {
    const oldAsOfPayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      as_of: "2026-07-01T08:00:00Z", // Payload generated 35 days ago (> 7 days staleAfterMs)
    };

    const state = mapBiomarkersPayloadToPresentation(oldAsOfPayload, mockContext);
    expect(state.kind).toBe("stale");
  });

  it("null data_as_of does not produce errors or fake date", () => {
    const nullDataAsOfPayload: BiomarkersDashboardPayloadV1 = {
      ...validReadyPayload,
      metadata: { ...validReadyPayload.metadata, data_as_of: null },
      summary: { ...validReadyPayload.summary, latest_collection_date: null },
    };

    const state = mapBiomarkersPayloadToPresentation(nullDataAsOfPayload, mockContext);
    expect(state.kind).toBe("ready");
    if (state.kind === "ready") {
      expect(state.presentation.latestCollectionLabel).toBe("Brak daty pobrania");
    }
  });

  it("presents laboratory_flag without reinterpretation", () => {
    const state = mapBiomarkersPayloadToPresentation(validReadyPayload, mockContext);
    if (state.kind === "ready") {
      const item = state.presentation.categories[0].biomarkers[0];
      expect(item.laboratoryFlag).toBe("H"); // Raw string preserved
    }
  });

  it("presents increasing trend direction neutrally", () => {
    const state = mapBiomarkersPayloadToPresentation(validReadyPayload, mockContext);
    if (state.kind === "ready") {
      const item = state.presentation.categories[0].biomarkers[0];
      expect(item.trendLabel).toBe("Trend rosnący");
      expect(item.trendDirection).toBe("increasing");
      // Confirm no diagnostic rating attached
      expect(item).not.toHaveProperty("isGood");
    }
  });
  it("returns failure state for malformed payload input", () => {
    const state = parseAndMapBiomarkersPayloadToPresentation({ invalid: "data" }, mockContext);
    expect(state.kind).toBe("failure");
  });
});

describe("Routing and View Resolutions", () => {
  it("resolves view=biomarkers in view-routing", () => {
    expect(resolveApplicationView("?view=biomarkers")).toBe("biomarkers");
    expect(searchForView("?source=http", "biomarkers")).toBe("?source=http&view=biomarkers");
  });

  it("resolves preview state for all state kinds", () => {
    const states = ["ready", "partial", "unavailable", "stale", "loading", "failure"] as const;
    for (const st of states) {
      const res = resolveBiomarkersPreviewState(`?view=biomarkers&state=${st}`, biomarkersPreviewStates);
      expect(res.kind).toBe(st);
    }
  });
});
