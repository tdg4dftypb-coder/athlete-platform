import type { BiomarkersDashboardPayloadV1 } from "./biomarkers-payload-v1";

export type ParseIssue = {
  readonly path: string;
  readonly message: string;
};

export type ParseResult<T> =
  | { readonly success: true; readonly data: T }
  | { readonly success: false; readonly issues: readonly ParseIssue[] };

const VALID_STATUSES = new Set(["ready", "partial", "unavailable"]);
const VALID_VERIFICATION_STATUSES = new Set(["verified", "unverified", "rejected"]);
const VALID_TREND_DIRECTIONS = new Set(["increasing", "decreasing", "stable", "unavailable"]);

export function parseBiomarkersDashboardPayloadV1(input: unknown): ParseResult<BiomarkersDashboardPayloadV1> {
  const issues: ParseIssue[] = [];

  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return { success: false, issues: [{ path: "payload", message: "Payload must be a dictionary object." }] };
  }

  const record = input as Record<string, unknown>;

  // 1. Privacy Check: reject forbidden private fields in root
  if ("source_document_hash" in record || "filename" in record || "original_filename" in record) {
    return { success: false, issues: [{ path: "payload", message: "Privacy violation: private document fields present in payload." }] };
  }

  // 2. contract_version
  if (record.contract_version !== "1.0") {
    issues.push({ path: "contract_version", message: `Expected contract_version '1.0', got '${String(record.contract_version)}'.` });
  }

  // 3. as_of ISO timestamp
  if (typeof record.as_of !== "string" || !isIsoTimestamp(record.as_of)) {
    issues.push({ path: "as_of", message: "as_of must be a valid ISO timestamp string." });
  }

  // 4. metadata
  if (typeof record.metadata !== "object" || record.metadata === null) {
    issues.push({ path: "metadata", message: "metadata must be an object." });
  } else {
    const meta = record.metadata as Record<string, unknown>;
    if (typeof meta.status !== "string" || !VALID_STATUSES.has(meta.status)) {
      issues.push({ path: "metadata.status", message: `Invalid status '${String(meta.status)}'.` });
    }
    if (typeof meta.completeness_score !== "number" || !Number.isFinite(meta.completeness_score) || meta.completeness_score < 0 || meta.completeness_score > 1) {
      issues.push({ path: "metadata.completeness_score", message: "completeness_score must be a finite number between 0.0 and 1.0." });
    }
    if (meta.data_as_of !== null && (typeof meta.data_as_of !== "string" || !isIsoTimestamp(meta.data_as_of))) {
      issues.push({ path: "metadata.data_as_of", message: "data_as_of must be null or a valid ISO timestamp string." });
    }
  }

  // 5. summary
  if (typeof record.summary !== "object" || record.summary === null) {
    issues.push({ path: "summary", message: "summary must be an object." });
  } else {
    const sum = record.summary as Record<string, unknown>;
    const intKeys = ["total_reports", "active_reports", "total_observations", "verified_observations", "unresolved_observations", "possible_duplicates"];
    for (const key of intKeys) {
      if (typeof sum[key] !== "number" || !Number.isInteger(sum[key]) || (sum[key] as number) < 0) {
        issues.push({ path: `summary.${key}`, message: `${key} must be a non-negative integer.` });
      }
    }
  }

  // 6. categories structure & enum checks
  if (!Array.isArray(record.categories)) {
    issues.push({ path: "categories", message: "categories must be an array." });
  } else {
    for (let cIdx = 0; cIdx < record.categories.length; cIdx++) {
      const cat = record.categories[cIdx];
      if (typeof cat !== "object" || cat === null) {
        issues.push({ path: `categories[${cIdx}]`, message: "Category item must be an object." });
        continue;
      }
      const catObj = cat as Record<string, unknown>;
      if (!Array.isArray(catObj.biomarkers)) {
        issues.push({ path: `categories[${cIdx}].biomarkers`, message: "biomarkers must be an array." });
      } else {
        for (let bIdx = 0; bIdx < catObj.biomarkers.length; bIdx++) {
          const b = catObj.biomarkers[bIdx];
          if (typeof b !== "object" || b === null) {
            issues.push({ path: `categories[${cIdx}].biomarkers[${bIdx}]`, message: "Biomarker item must be an object." });
            continue;
          }
          const bObj = b as Record<string, unknown>;
          if (typeof bObj.verification_status !== "string" || !VALID_VERIFICATION_STATUSES.has(bObj.verification_status)) {
            issues.push({ path: `categories[${cIdx}].biomarkers[${bIdx}].verification_status`, message: `Invalid verification_status '${String(bObj.verification_status)}'.` });
          }
          if (typeof bObj.trend_direction !== "string" || !VALID_TREND_DIRECTIONS.has(bObj.trend_direction)) {
            issues.push({ path: `categories[${cIdx}].biomarkers[${bIdx}].trend_direction`, message: `Invalid trend_direction '${String(bObj.trend_direction)}'.` });
          }
        }
      }
    }
  }

  // 7. unresolved_items & privacy check for raw_value
  if (!Array.isArray(record.unresolved_items)) {
    issues.push({ path: "unresolved_items", message: "unresolved_items must be an array." });
  } else {
    for (let i = 0; i < record.unresolved_items.length; i++) {
      const item = record.unresolved_items[i];
      if (typeof item === "object" && item !== null && "raw_value" in item) {
        issues.push({ path: `unresolved_items[${i}].raw_value`, message: "Privacy violation: raw_value present in unresolved summary item." });
      }
    }
  }

  // 8. Finite numbers check across whole object
  const nonFinitePath = findNonFiniteNumberPath(record, "payload");
  if (nonFinitePath) {
    issues.push({ path: nonFinitePath, message: "Non-finite number value (NaN / Infinity) is forbidden." });
  }

  if (issues.length > 0) {
    return { success: false, issues };
  }

  return { success: true, data: input as BiomarkersDashboardPayloadV1 };
}

function isIsoTimestamp(val: string): boolean {
  if (typeof val !== "string" || val.trim().length === 0) return false;
  const d = new Date(val);
  return !isNaN(d.getTime());
}

function findNonFiniteNumberPath(obj: unknown, currentPath: string): string | null {
  if (typeof obj === "number") {
    if (!Number.isFinite(obj)) return currentPath;
  } else if (typeof obj === "object" && obj !== null) {
    if (Array.isArray(obj)) {
      for (let i = 0; i < obj.length; i++) {
        const res = findNonFiniteNumberPath(obj[i], `${currentPath}[${i}]`);
        if (res) return res;
      }
    } else {
      for (const [k, v] of Object.entries(obj)) {
        const res = findNonFiniteNumberPath(v, `${currentPath}.${k}`);
        if (res) return res;
      }
    }
  }
  return null;
}
