import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type {
  AthleteDashboardPayloadV1,
  DashboardSectionStatus,
} from "../contracts/athlete-dashboard-payload-v1";
import type {
  RecoveryDetailPresentation,
  RecoveryFactorPresentation,
  RecoveryPresentation,
  RecoveryPresentationHeader,
} from "../models/recovery-presentation";
import type { RecoveryPresentationState } from "../models/recovery-presentation-state";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";
import type { MappingContext } from "./mapping-context";

export type PayloadMappedRecoveryState = Exclude<
  RecoveryPresentationState,
  { kind: "loading" }
>;

export function parseAndMapAthleteDashboardToRecovery(
  input: unknown,
  context: MappingContext,
): PayloadMappedRecoveryState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) {
    return failureState(
      `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
      context,
    );
  }
  return mapAthleteDashboardToRecovery(parsed.data, context);
}

export function mapAthleteDashboardToRecovery(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedRecoveryState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return failureState("Payload zawiera niespójny kontekst czasu.", context);
  }

  const stale = payload.valid_for_date !== dateInTimeZone(context.now, context.timeZone)
    || ageMs > context.staleAfterMs;
  const header = createHeader(payload, context, stale);
  if (payload.recovery.metadata.status === "unavailable") {
    return {
      kind: "unavailable",
      header,
      message: "Ocena regeneracji nie jest teraz dostępna.",
      reason: "Brakuje źródłowych danych potrzebnych do pokazania oceny.",
      nextAction: "Sprawdź ponownie po kolejnej synchronizacji danych.",
    };
  }

  const recovery = createRecovery(payload, context, header);
  if (stale) {
    return {
      kind: "stale",
      recovery,
      message: "Ta ocena regeneracji może nie opisywać dzisiejszego stanu.",
      lastUpdatedText: header.lastUpdatedText,
    };
  }

  const missingData = collectMissingData(payload);
  if (missingData.length > 0) {
    return {
      kind: "partial",
      recovery,
      message: "Ocena jest dostępna, ale część czynników ma niepełne dane.",
      missingData,
    };
  }

  return { kind: "ready", recovery };
}

function createHeader(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  stale: boolean,
): RecoveryPresentationHeader {
  const date = parseContractDate(payload.valid_for_date);
  const asOf = parseContractTimestamp(payload.as_of);
  return {
    title: "Regeneracja",
    dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
      weekday: "long",
      day: "numeric",
      month: "long",
      timeZone: context.timeZone,
    }).format(date),
    lastUpdatedText: `Ostatnia aktualizacja: ${formatContractDateTime(asOf, context)}`,
    freshnessLabel: stale ? "Dane nieaktualne" : "Aktualne",
  };
}

function createRecovery(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  header: RecoveryPresentationHeader,
): RecoveryPresentation {
  const partial = collectMissingData(payload).length > 0;
  return {
    source: "payload",
    header,
    hero: {
      statusLabel: partial ? "Ocena częściowa" : "Ocena regeneracji dostępna",
      narrative: partial
        ? "Wynik pochodzi z dostępnych pomiarów. Brakujące źródła zwiększają niepewność prezentacji."
        : "Dzisiejsza ocena została wyliczona na podstawie dostępnych danych o regeneracji. Poniżej zobaczysz dostępne pomiary.",
      score: payload.recovery.recovery_score,
      scoreLabel: payload.recovery.recovery_score === null
        ? null
        : "Poziom regeneracji",
      tone: partial ? "caution" : "positive",
    },
    factors: createFactors(payload, context),
    interpretation: createInterpretation(payload),
    details: createDetails(payload, context),
    trendSummary: null,
  };
}

function createFactors(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): readonly RecoveryFactorPresentation[] {
  return [
    createFactor({
      id: "hrv",
      label: "HRV",
      valueText: formatOptional(payload.health.hrv_ms, "ms", context),
      status: payload.health.metadata.status,
      description: payload.health.hrv_ms === null
        ? "Dzisiejszy pomiar HRV nie jest dostępny."
        : "Dzisiejszy pomiar HRV jest dostępny w odprawie.",
    }),
    createFactor({
      id: "sleep",
      label: "Sen",
      valueText: formatSleep(payload.health.sleep_minutes),
      contextText: payload.recovery.sleep_score === null
        ? null
        : `Ocena snu: ${formatNumber(payload.recovery.sleep_score, context)}/100`,
      status: combineStatuses(
        payload.health.metadata.status,
        payload.recovery.metadata.status,
      ),
      description: payload.health.sleep_minutes === null
        ? "Czas snu nie jest dostępny."
        : "Czas snu i jego ocena pochodzą z dzisiejszych danych.",
    }),
    createFactor({
      id: "resting-heart-rate",
      label: "Tętno spoczynkowe",
      valueText: formatOptional(
        payload.health.resting_heart_rate_bpm,
        "ud./min",
        context,
      ),
      status: payload.health.metadata.status,
      description: payload.health.resting_heart_rate_bpm === null
        ? "Dzisiejsze tętno spoczynkowe nie jest dostępne."
        : "Dzisiejsze tętno spoczynkowe jest dostępne w odprawie.",
    }),
    createFactor({
      id: "fatigue",
      label: "Zmęczenie",
      valueText: formatFatigueValue(payload.performance.fatigue_tss_per_day, context),
      status: payload.performance.metadata.status,
      description: payload.performance.fatigue_tss_per_day === null
        ? "Bieżący poziom zmęczenia nie jest dostępny."
        : "Wartość zmęczenia pochodzi z bieżącego stanu obciążenia.",
    }),
  ];
}

function formatFatigueValue(val: number | null, context: MappingContext): string | null {
  if (val === null) return null;
  if (val <= 5) return `Niski poziom (${formatNumber(val, context)} TSS)`;
  if (val <= 35) return `Umiarkowany poziom (${formatNumber(val, context)} TSS)`;
  return `Wysoki poziom (${formatNumber(val, context)} TSS)`;
}

function createFactor(input: {
  id: RecoveryFactorPresentation["id"];
  label: string;
  valueText: string | null;
  contextText?: string | null;
  status: DashboardSectionStatus;
  description: string;
}): RecoveryFactorPresentation {
  const missing = input.valueText === null;
  return {
    id: input.id,
    label: input.label,
    statusLabel: missing
      ? "Brak danych"
      : input.status === "ready" ? "Dostępne" : "Dane częściowe",
    valueText: input.valueText,
    contextText: input.contextText ?? null,
    description: input.description,
    trendText: null,
    tone: missing ? "neutral" : input.status === "ready" ? "positive" : "caution",
  };
}

function createInterpretation(payload: AthleteDashboardPayloadV1): string {
  if (payload.training.decision_reasons.includes("adaptation_reduce_load")) {
    return "Dzisiejsze obciążenie zostało dostosowane w decyzji treningowej.";
  }
  if (payload.training.decision_reasons.includes("insight_need_more_recovery")) {
    return "Dzisiejszy plan uwzględnia potrzebę większej regeneracji.";
  }
  if (payload.training.metadata.status !== "unavailable") {
    return "Ocena regeneracji została uwzględniona w dzisiejszym planie treningowym.";
  }
  return "Ocena regeneracji jest dostępna niezależnie od szczegółów planu treningowego.";
}

function createDetails(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): readonly RecoveryDetailPresentation[] {
  const details: RecoveryDetailPresentation[] = [];
  if (payload.health.respiratory_rate_per_minute !== null) {
    details.push({
      id: "respiratory-rate",
      label: "Częstość oddechu",
      valueText: `${formatNumber(payload.health.respiratory_rate_per_minute, context)} /min`,
      description: "Bieżący pomiar oddechu w spoczynku.",
    });
  }
  if (payload.health.oxygen_saturation_percent !== null) {
    details.push({
      id: "oxygen-saturation",
      label: "Saturacja",
      valueText: `${formatNumber(payload.health.oxygen_saturation_percent, context)}%`,
      description: "Bieżący pomiar nasycenia krwi tlenem.",
    });
  }
  return details;
}

function collectMissingData(payload: AthleteDashboardPayloadV1): readonly string[] {
  const missing = new Set<string>();
  if (payload.recovery.recovery_score === null) missing.add("Brak wskaźnika regeneracji");
  if (payload.health.hrv_ms === null) missing.add("Brak HRV");
  if (payload.health.sleep_minutes === null) missing.add("Brak czasu snu");
  if (payload.health.resting_heart_rate_bpm === null) {
    missing.add("Brak tętna spoczynkowego");
  }
  if (payload.performance.fatigue_tss_per_day === null) {
    missing.add("Brak bieżącego zmęczenia");
  }
  if (payload.recovery.metadata.status === "partial") {
    missing.add("Ocena regeneracji jest częściowa");
  }
  if (payload.health.metadata.status !== "ready") {
    missing.add("Dane zdrowotne są niepełne");
  }
  if (payload.performance.metadata.status !== "ready") {
    missing.add("Dane obciążenia są niepełne");
  }
  return [...missing];
}

function failureState(
  supportingText: string,
  context: MappingContext,
): PayloadMappedRecoveryState {
  return {
    kind: "failure",
    header: {
      title: "Regeneracja",
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long",
        day: "numeric",
        month: "long",
        timeZone: context.timeZone,
      }).format(context.now),
      lastUpdatedText: "Aktualizacja niedostępna",
      freshnessLabel: null,
    },
    message: "Nie udało się teraz przygotować widoku regeneracji.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}

function combineStatuses(
  first: DashboardSectionStatus,
  second: DashboardSectionStatus,
): DashboardSectionStatus {
  if (first === "unavailable" || second === "unavailable") return "unavailable";
  if (first === "partial" || second === "partial") return "partial";
  return "ready";
}

function formatOptional(
  value: number | null,
  unit: string,
  context: MappingContext,
): string | null {
  return value === null ? null : `${formatNumber(value, context)} ${unit}`;
}

function formatNumber(value: number, context: MappingContext): string {
  return new Intl.NumberFormat(context.locale ?? "pl-PL", {
    maximumFractionDigits: 1,
  }).format(value);
}

function formatSleep(minutes: number | null): string | null {
  if (minutes === null) return null;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours} godz. ${remainder} min`;
}
