/**
 * Sprint 7F — Biomarker History Experience Tests
 *
 * Covers: parser, presentation states, measurement rendering,
 * ordering, privacy audit, qualitative/numeric variants.
 */

import { describe, it, expect } from "vitest";
import { parseHistoryPayloadV1 } from "../src/biomarkers/history/history-payload-parser";
import {
  mapHistoryPayloadToPresentation,
} from "../src/biomarkers/history/history-presentation";
import { createHistoryExperienceApp } from "../src/biomarkers/history/history-experience-view";
import type { HistoryPayloadV1 } from "../src/biomarkers/history/history-payload-parser";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VALID_PAYLOAD: HistoryPayloadV1 = {
  contract_version: "1.0",
  canonical_code: "ferritin",
  display_name: "Ferrytyna",
  preferred_unit: "ng/mL",
  measurements: [
    {
      collected_at: "2026-01-15T00:00:00+00:00",
      numeric_value: 42.5,
      qualitative_value: null,
      laboratory_flag: null,
      verification_status: "verified",
    },
    {
      collected_at: "2026-04-10T00:00:00+00:00",
      numeric_value: 38.0,
      qualitative_value: null,
      laboratory_flag: "L",
      verification_status: "unverified",
    },
  ],
};

const QUALITATIVE_PAYLOAD: HistoryPayloadV1 = {
  contract_version: "1.0",
  canonical_code: "hbsag",
  display_name: "HBsAg",
  preferred_unit: "",
  measurements: [
    {
      collected_at: "2026-03-01T00:00:00+00:00",
      numeric_value: null,
      qualitative_value: "Nieobecny",
      laboratory_flag: null,
      verification_status: "unverified",
    },
  ],
};

const TEST_CTX = { locale: "pl-PL", timeZone: "Europe/Warsaw" };

// ---------------------------------------------------------------------------
// 1. Parser — valid payload
// ---------------------------------------------------------------------------

describe("parseHistoryPayloadV1", () => {
  it("parses a valid payload successfully", () => {
    const result = parseHistoryPayloadV1(VALID_PAYLOAD);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.canonical_code).toBe("ferritin");
      expect(result.data.measurements).toHaveLength(2);
    }
  });

  it("rejects non-object input", () => {
    const result = parseHistoryPayloadV1("not an object");
    expect(result.success).toBe(false);
  });

  it("rejects missing contract_version", () => {
    const bad = { ...VALID_PAYLOAD, contract_version: "2.0" } as unknown;
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.issues.some((i) => i.path === "contract_version")).toBe(true);
    }
  });

  it("rejects empty canonical_code", () => {
    const bad = { ...VALID_PAYLOAD, canonical_code: "" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.issues.some((i) => i.path === "canonical_code")).toBe(true);
    }
  });

  it("rejects measurements that are not an array", () => {
    const bad = { ...VALID_PAYLOAD, measurements: "not-an-array" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.issues.some((i) => i.path === "measurements")).toBe(true);
    }
  });

  it("rejects invalid verification_status in measurement", () => {
    const bad = {
      ...VALID_PAYLOAD,
      measurements: [{ ...VALID_PAYLOAD.measurements[0], verification_status: "unknown" }],
    };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.issues.some((i) => i.path.includes("verification_status"))).toBe(true);
    }
  });

  // -------------------------------------------------------------------------
  // Privacy audit
  // -------------------------------------------------------------------------

  it("rejects payload containing raw_value (privacy guard)", () => {
    const bad = { ...VALID_PAYLOAD, raw_value: "secret" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.issues.some((i) => i.message.includes("privacy") || i.message.toLowerCase().includes("private"))).toBe(true);
    }
  });

  it("rejects payload containing observation_id (privacy guard)", () => {
    const bad = { ...VALID_PAYLOAD, observation_id: "obs-123" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
  });

  it("rejects payload containing source_document_hash (privacy guard)", () => {
    const bad = { ...VALID_PAYLOAD, source_document_hash: "abc123" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
  });

  it("rejects payload containing report_id (privacy guard)", () => {
    const bad = { ...VALID_PAYLOAD, report_id: "rpt-999" };
    const result = parseHistoryPayloadV1(bad);
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 2. Presentation mapping — numeric biomarker
// ---------------------------------------------------------------------------

describe("mapHistoryPayloadToPresentation — numeric", () => {
  it("maps title and unit from payload", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    expect(pres.title).toBe("Ferrytyna");
    expect(pres.unit).toBe("ng/mL");
  });

  it("sets totalMeasurements correctly", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    expect(pres.totalMeasurements).toBe(2);
  });

  it("latestMeasurement is the last in the array (newest)", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    expect(pres.latestMeasurement).not.toBeNull();
    expect(pres.latestMeasurement?.numericValue).toBe(38.0);
  });

  it("numeric measurement includes unit in valueLabel", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    const first = pres.measurements[0];
    expect(first.valueLabel).toContain("ng/mL");
    expect(first.numericValue).toBe(42.5);
  });

  it("maps laboratory_flag to flagLabel", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    const second = pres.measurements[1];
    expect(second.flagLabel).toContain("L");
  });

  it("null laboratory_flag → null flagLabel", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    const first = pres.measurements[0];
    expect(first.flagLabel).toBeNull();
  });

  it("verified → 'Zweryfikowano'", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    expect(pres.measurements[0].verificationLabel).toBe("Zweryfikowano");
  });

  it("unverified → 'Niezweryfikowane'", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    expect(pres.measurements[1].verificationLabel).toBe("Niezweryfikowane");
  });
});

// ---------------------------------------------------------------------------
// 3. Presentation mapping — qualitative biomarker
// ---------------------------------------------------------------------------

describe("mapHistoryPayloadToPresentation — qualitative", () => {
  it("qualitative measurement has no unit in valueLabel", () => {
    const pres = mapHistoryPayloadToPresentation(QUALITATIVE_PAYLOAD, TEST_CTX);
    expect(pres.measurements[0].valueLabel).toBe("Nieobecny");
    expect(pres.measurements[0].unit).toBe("");
  });

  it("qualitativeValue is preserved", () => {
    const pres = mapHistoryPayloadToPresentation(QUALITATIVE_PAYLOAD, TEST_CTX);
    expect(pres.measurements[0].qualitativeValue).toBe("Nieobecny");
    expect(pres.measurements[0].numericValue).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 4. Ordering preserved
// ---------------------------------------------------------------------------

describe("ordering", () => {
  it("preserves API order oldest → newest in measurements array", () => {
    const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);
    // First measurement should be Jan, second Apr
    const firstDate = new Date(VALID_PAYLOAD.measurements[0].collected_at).getTime();
    const secondDate = new Date(VALID_PAYLOAD.measurements[1].collected_at).getTime();
    expect(firstDate).toBeLessThan(secondDate);
    // Both should be present, in same order
    expect(pres.measurements).toHaveLength(2);
    expect(pres.measurements[0].numericValue).toBe(42.5);
    expect(pres.measurements[1].numericValue).toBe(38.0);
  });
});

// ---------------------------------------------------------------------------
// 5. View states — DOM rendering
// ---------------------------------------------------------------------------

describe("createHistoryExperienceApp — loading", () => {
  it("renders loading state with aria-busy", () => {
    const el = createHistoryExperienceApp(
      { kind: "loading", message: "Wczytywanie..." },
      () => {},
    );
    const busy = el.querySelector("[aria-busy='true']");
    expect(busy).not.toBeNull();
  });
});

describe("createHistoryExperienceApp — failure", () => {
  it("renders failure state with error title", () => {
    const el = createHistoryExperienceApp(
      { kind: "failure", title: "Błąd połączenia", message: "Nie udało się pobrać." },
      () => {},
    );
    expect(el.textContent).toContain("Błąd połączenia");
    expect(el.textContent).toContain("Nie udało się pobrać.");
  });
});

describe("createHistoryExperienceApp — unavailable / empty history", () => {
  it("renders unavailable state", () => {
    const el = createHistoryExperienceApp(
      { kind: "unavailable", title: "ferritin", message: "Brak historii pomiarów." },
      () => {},
    );
    expect(el.textContent).toContain("Brak historii pomiarów.");
  });

  it("ready state with empty measurements renders empty notice", () => {
    const el = createHistoryExperienceApp(
      {
        kind: "ready",
        presentation: {
          title: "Ferrytyna",
          unit: "ng/mL",
          totalMeasurements: 0,
          latestMeasurement: null,
          measurements: [],
        },
      },
      () => {},
    );
    expect(el.textContent).toContain("Brak historii pomiarów.");
  });
});

describe("createHistoryExperienceApp — ready", () => {
  const pres = mapHistoryPayloadToPresentation(VALID_PAYLOAD, TEST_CTX);

  it("renders measurement list items", () => {
    const el = createHistoryExperienceApp({ kind: "ready", presentation: pres }, () => {});
    const items = el.querySelectorAll(".history-measurement-row");
    expect(items.length).toBe(2);
  });

  it("renders hero card with latest value", () => {
    const el = createHistoryExperienceApp({ kind: "ready", presentation: pres }, () => {});
    const hero = el.querySelector(".history-hero");
    expect(hero).not.toBeNull();
    // latest measurement is 38.0
    expect(hero?.textContent).toContain("38");
  });

  it("renders laboratory flag when present", () => {
    const el = createHistoryExperienceApp({ kind: "ready", presentation: pres }, () => {});
    expect(el.textContent).toContain("Flaga laboratorium: L");
  });

  it("does not expose private fields in rendered DOM", () => {
    const el = createHistoryExperienceApp({ kind: "ready", presentation: pres }, () => {});
    const html = el.innerHTML;
    const forbidden = [
      "observation_id",
      "report_id",
      "import_run_id",
      "source_document_hash",
      "filename",
      "original_filename",
      "raw_value",
    ];
    for (const field of forbidden) {
      expect(html).not.toContain(field);
    }
  });
});
