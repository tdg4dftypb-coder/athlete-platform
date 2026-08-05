/**
 * Sprint 7F — History Payload Parser
 *
 * Validates HistoryPayloadV1 runtime structure.
 * Rejects any payload containing private/internal fields (privacy guard).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ParseIssue {
  readonly path: string;
  readonly message: string;
}

export type ParseResult<T> =
  | { readonly success: true; readonly data: T }
  | { readonly success: false; readonly issues: readonly ParseIssue[] };

/** TypeScript shape of HistoryPayloadV1 after successful parse. */
export interface HistoryMeasurementPayloadV1 {
  readonly collected_at: string;
  readonly numeric_value: number | null;
  readonly qualitative_value: string | null;
  readonly laboratory_flag: string | null;
  readonly verification_status: "verified" | "unverified" | "rejected";
}

export interface HistoryPayloadV1 {
  readonly contract_version: "1.0";
  readonly canonical_code: string;
  readonly display_name: string;
  readonly preferred_unit: string;
  readonly measurements: readonly HistoryMeasurementPayloadV1[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VALID_VERIFICATION_STATUSES = new Set(["verified", "unverified", "rejected"]);

/**
 * Fields that must NEVER appear in a public history payload.
 * Parser rejects any payload containing these keys anywhere at the root level.
 */
const FORBIDDEN_PRIVATE_FIELDS = [
  "observation_id",
  "report_id",
  "import_run_id",
  "source_document_hash",
  "filename",
  "original_filename",
  "raw_value",
] as const;

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

export function parseHistoryPayloadV1(input: unknown): ParseResult<HistoryPayloadV1> {
  const issues: ParseIssue[] = [];

  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return {
      success: false,
      issues: [{ path: "payload", message: "Payload must be a non-null object." }],
    };
  }

  const record = input as Record<string, unknown>;

  // 1. Privacy guard — reject forbidden private fields at root level
  for (const field of FORBIDDEN_PRIVATE_FIELDS) {
    if (field in record) {
      return {
        success: false,
        issues: [
          {
            path: field,
            message: `Privacy violation: private field '${field}' is present in history payload.`,
          },
        ],
      };
    }
  }

  // 2. contract_version
  if (record["contract_version"] !== "1.0") {
    issues.push({
      path: "contract_version",
      message: `Expected contract_version '1.0', got '${String(record["contract_version"])}'.`,
    });
  }

  // 3. canonical_code
  if (typeof record["canonical_code"] !== "string" || record["canonical_code"].trim() === "") {
    issues.push({
      path: "canonical_code",
      message: "canonical_code must be a non-empty string.",
    });
  }

  // 4. display_name
  if (typeof record["display_name"] !== "string") {
    issues.push({
      path: "display_name",
      message: "display_name must be a string.",
    });
  }

  // 5. preferred_unit
  if (typeof record["preferred_unit"] !== "string") {
    issues.push({
      path: "preferred_unit",
      message: "preferred_unit must be a string.",
    });
  }

  // 6. measurements array
  if (!Array.isArray(record["measurements"])) {
    issues.push({
      path: "measurements",
      message: "measurements must be an array.",
    });
  } else {
    for (let i = 0; i < record["measurements"].length; i++) {
      const m = record["measurements"][i];
      const mIssues = validateMeasurement(m, i);
      issues.push(...mIssues);
    }
  }

  if (issues.length > 0) {
    return { success: false, issues };
  }

  return { success: true, data: input as HistoryPayloadV1 };
}

function validateMeasurement(m: unknown, index: number): ParseIssue[] {
  const issues: ParseIssue[] = [];
  const base = `measurements[${index}]`;

  if (typeof m !== "object" || m === null || Array.isArray(m)) {
    issues.push({ path: base, message: "Measurement must be a non-null object." });
    return issues;
  }

  const mObj = m as Record<string, unknown>;

  // Privacy guard on measurement level
  for (const field of FORBIDDEN_PRIVATE_FIELDS) {
    if (field in mObj) {
      issues.push({
        path: `${base}.${field}`,
        message: `Privacy violation: private field '${field}' in measurement.`,
      });
    }
  }

  // collected_at — must be ISO 8601 string
  if (typeof mObj["collected_at"] !== "string" || !isIsoTimestamp(mObj["collected_at"])) {
    issues.push({
      path: `${base}.collected_at`,
      message: "collected_at must be a valid ISO 8601 timestamp string.",
    });
  }

  // numeric_value — number or null
  if (mObj["numeric_value"] !== null && typeof mObj["numeric_value"] !== "number") {
    issues.push({
      path: `${base}.numeric_value`,
      message: "numeric_value must be a number or null.",
    });
  }
  if (typeof mObj["numeric_value"] === "number" && !Number.isFinite(mObj["numeric_value"])) {
    issues.push({
      path: `${base}.numeric_value`,
      message: "numeric_value must be finite (NaN/Infinity are forbidden).",
    });
  }

  // qualitative_value — string or null
  if (mObj["qualitative_value"] !== null && typeof mObj["qualitative_value"] !== "string") {
    issues.push({
      path: `${base}.qualitative_value`,
      message: "qualitative_value must be a string or null.",
    });
  }

  // laboratory_flag — string or null
  if (mObj["laboratory_flag"] !== null && typeof mObj["laboratory_flag"] !== "string") {
    issues.push({
      path: `${base}.laboratory_flag`,
      message: "laboratory_flag must be a string or null.",
    });
  }

  // verification_status — enum
  if (
    typeof mObj["verification_status"] !== "string" ||
    !VALID_VERIFICATION_STATUSES.has(mObj["verification_status"])
  ) {
    issues.push({
      path: `${base}.verification_status`,
      message: `verification_status must be one of: verified, unverified, rejected. Got '${String(mObj["verification_status"])}'.`,
    });
  }

  return issues;
}

function isIsoTimestamp(val: string): boolean {
  if (val.trim().length === 0) return false;
  const d = new Date(val);
  return !isNaN(d.getTime());
}
