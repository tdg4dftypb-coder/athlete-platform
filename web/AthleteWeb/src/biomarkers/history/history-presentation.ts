/**
 * Sprint 7F — History Presentation Model
 *
 * UI model for the Biomarker History Experience.
 * Has no knowledge of the backend payload structure.
 */

// ---------------------------------------------------------------------------
// Measurement presentation
// ---------------------------------------------------------------------------

export interface HistoryMeasurementPresentation {
  /** Human-readable date label, e.g. "18 sty 2024" */
  readonly collectedAtLabel: string;
  /** Formatted value with unit if numeric, or qualitative text if qualitative, e.g. "42.5 ng/mL" | "Nieobecny" */
  readonly valueLabel: string;
  /** Raw numeric value for accessibility / screen-reader use */
  readonly numericValue: number | null;
  /** Raw qualitative value */
  readonly qualitativeValue: string | null;
  /** Unit string for numeric measurements, empty string for qualitative */
  readonly unit: string;
  /** Formatted lab flag label, e.g. "Flaga laboratorium: H", or null */
  readonly flagLabel: string | null;
  /** Human-readable verification label */
  readonly verificationLabel: string;
}

// ---------------------------------------------------------------------------
// Top-level presentation
// ---------------------------------------------------------------------------

export interface HistoryPresentation {
  /** Biomarker display name, e.g. "Ferrytyna" */
  readonly title: string;
  /** Preferred unit string, e.g. "ng/mL" (may be empty) */
  readonly unit: string;
  /** Total number of measurements */
  readonly totalMeasurements: number;
  /** Most recent measurement (last in the ordered list), or null if empty */
  readonly latestMeasurement: HistoryMeasurementPresentation | null;
  /** All measurements in chronological order (oldest → newest), as delivered by the API */
  readonly measurements: readonly HistoryMeasurementPresentation[];
}

// ---------------------------------------------------------------------------
// Presentation state (4 states)
// ---------------------------------------------------------------------------

export type HistoryPresentationState =
  | {
      readonly kind: "loading";
      readonly message: string;
    }
  | {
      readonly kind: "ready";
      readonly presentation: HistoryPresentation;
    }
  | {
      readonly kind: "failure";
      readonly title: string;
      readonly message: string;
    }
  | {
      readonly kind: "unavailable";
      readonly title: string;
      readonly message: string;
    };

// ---------------------------------------------------------------------------
// Mapper: HistoryPayloadV1 → HistoryPresentation
// ---------------------------------------------------------------------------

import type {
  HistoryPayloadV1,
  HistoryMeasurementPayloadV1,
} from "./history-payload-parser";

export interface HistoryMappingContext {
  readonly locale?: string;
  readonly timeZone?: string;
}

export function mapHistoryPayloadToPresentation(
  payload: HistoryPayloadV1,
  context: HistoryMappingContext = {},
): HistoryPresentation {
  const unit = payload.preferred_unit ?? "";

  const measurements: HistoryMeasurementPresentation[] = payload.measurements.map((m) =>
    mapMeasurement(m, unit, context),
  );

  const latestMeasurement =
    measurements.length > 0 ? measurements[measurements.length - 1] : null;

  return {
    title: payload.display_name,
    unit,
    totalMeasurements: measurements.length,
    latestMeasurement,
    measurements,
  };
}

function mapMeasurement(
  m: HistoryMeasurementPayloadV1,
  unit: string,
  context: HistoryMappingContext,
): HistoryMeasurementPresentation {
  const collectedAtLabel = formatDate(m.collected_at, context);

  // Value label: prefer numeric, fall back to qualitative
  let valueLabel: string;
  let effectiveUnit: string;

  if (m.numeric_value !== null) {
    const formatted = formatNumber(m.numeric_value, context);
    effectiveUnit = unit;
    valueLabel = unit ? `${formatted} ${unit}` : formatted;
  } else if (m.qualitative_value !== null) {
    valueLabel = m.qualitative_value;
    effectiveUnit = "";
  } else {
    valueLabel = "Brak wartości";
    effectiveUnit = "";
  }

  const flagLabel = m.laboratory_flag
    ? `Flaga laboratorium: ${m.laboratory_flag}`
    : null;

  const verificationLabel = mapVerificationLabel(m.verification_status);

  return {
    collectedAtLabel,
    valueLabel,
    numericValue: m.numeric_value,
    qualitativeValue: m.qualitative_value,
    unit: effectiveUnit,
    flagLabel,
    verificationLabel,
  };
}

function mapVerificationLabel(status: string): string {
  switch (status) {
    case "verified":
      return "Zweryfikowano";
    case "rejected":
      return "Odrzucono";
    default:
      return "Niezweryfikowane";
  }
}

function formatDate(isoString: string, context: HistoryMappingContext): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString(context.locale ?? "pl-PL", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: context.timeZone,
    });
  } catch {
    return isoString;
  }
}

function formatNumber(val: number, context: HistoryMappingContext): string {
  return new Intl.NumberFormat(context.locale ?? "pl-PL", {
    maximumFractionDigits: 2,
  }).format(val);
}
