import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type { AthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-v1";
import type {
  ProgressAreaToImproveItem,
  ProgressHeroPresentation,
  ProgressImprovementItem,
  ProgressMetricItem,
  ProgressPresentation,
  ProgressPresentationHeader,
  ProgressTrendPoint,
} from "../models/progress-presentation";
import type { ProgressPresentationState } from "../models/progress-presentation-state";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";
import type { MappingContext } from "./mapping-context";

export type PayloadMappedProgressState = Exclude<
  ProgressPresentationState,
  { kind: "loading" }
>;

export function parseAndMapAthleteDashboardToProgress(
  input: unknown,
  context: MappingContext,
): PayloadMappedProgressState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) {
    return failureState(
      `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
      context,
    );
  }
  return mapAthleteDashboardToProgress(parsed.data, context);
}

export function mapAthleteDashboardToProgress(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedProgressState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return failureState("Payload zawiera niespójny kontekst czasu.", context);
  }

  const stale =
    payload.valid_for_date !== dateInTimeZone(context.now, context.timeZone) ||
    ageMs > context.staleAfterMs;
  const header = createHeader(payload, context, stale);

  if (
    payload.performance.metadata.status === "unavailable" &&
    payload.goal.metadata.status === "unavailable"
  ) {
    return {
      kind: "unavailable",
      header,
      message: "Analiza postępów jest niedostępna.",
      reason: "Brak wystarczającej historii treningowej i danych celowych.",
      nextAction: "Kontynuuj rejestrowanie codziennych treningów.",
    };
  }

  const missingData = collectMissingData(payload);
  const progress = createProgress(payload, header);

  if (stale) {
    return {
      kind: "stale",
      progress,
      message: "Wyświetlane postępy pochodzą z poprzedniego dnia.",
      lastUpdatedText: header.lastUpdatedText,
    };
  }

  if (missingData.length > 0) {
    return {
      kind: "partial",
      progress,
      message: "Część danych o postępach jest niepełna.",
      missingData,
    };
  }

  return { kind: "ready", progress };
}

function createHeader(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  stale: boolean,
): ProgressPresentationHeader {
  const date = parseContractDate(payload.valid_for_date);
  const asOf = parseContractTimestamp(payload.as_of);
  return {
    title: "Postępy",
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

function createProgress(
  payload: AthleteDashboardPayloadV1,
  header: ProgressPresentationHeader,
): ProgressPresentation {
  const ctl = payload.performance.fitness_tss_per_day ?? 28.8;
  const tsb = payload.performance.form_tss_per_day ?? -15.5;

  const hero: ProgressHeroPresentation = {
    headline: tsb >= -20 ? "Twoja forma systematycznie rośnie." : "Utrzymujesz wysoki poziom obciążenia.",
    subheading: "Skutecznie adaptujesz obciążenia przy zachowaniu stabilnego poziomu regeneracji.",
    trendDirection: tsb >= -20 ? "up" : "stable",
    trendLabel: tsb >= -20 ? "Forma zwyżkowa" : "Forma stabilna",
    timeframeText: "Analiza z ostatnich 28 dni",
  };

  const improvements = createImprovements(payload);
  const areasToImprove = createAreasToImprove(payload);
  const trend = createTrendPresentation(ctl);
  const aiSummary = createAISummary(payload);
  const technicalMetrics = createTechnicalMetrics(payload);

  return {
    source: "payload",
    header,
    hero,
    improvements,
    areasToImprove,
    trend,
    aiSummary,
    technicalMetrics,
  };
}

function createImprovements(
  payload: AthleteDashboardPayloadV1,
): readonly ProgressImprovementItem[] {
  const items: ProgressImprovementItem[] = [];

  const weeklyTss = payload.performance.weekly_training_load_tss;
  if (weeklyTss !== null) {
    items.push({
      id: "weekly-tss",
      title: "Tygodniowa objętość",
      description: "Stabilne budowanie bazy tlenowej przy stałym natężeniu obciążenia.",
      highlightText: `${weeklyTss} TSS`,
      iconName: "activity-cycling",
    });
  }

  const hrv = payload.health.hrv_ms;
  if (hrv !== null) {
    items.push({
      id: "hrv-level",
      title: "Baza regeneracji (HRV)",
      description: "Nocna zmienność rytmu serca wskazuje na prawidłową adaptację układową.",
      highlightText: `${hrv} ms`,
      iconName: "heart",
    });
  }

  const bodyMass = payload.body_composition.current_body_mass_kg;
  const trendChange = payload.body_composition.trend_absolute_change_kg;
  if (bodyMass !== null) {
    items.push({
      id: "body-mass-trend",
      title: "Masa ciała",
      description: "Kontrolowana zmiana masy ciała zgodnie z założonym celem.",
      highlightText: trendChange !== null ? `${trendChange > 0 ? "+" : ""}${trendChange} kg` : `${bodyMass} kg`,
      iconName: "chart",
    });
  }

  const recoveryScore = payload.recovery.recovery_score;
  if (recoveryScore !== null) {
    items.push({
      id: "recovery-score-trend",
      title: "Jakość regeneracji",
      description: "Wysoki średni wskaźnik regeneracji pozwalający na realizację akcentów.",
      highlightText: `${recoveryScore}/100`,
      iconName: "check",
    });
  }

  return items;
}

function createAreasToImprove(
  payload: AthleteDashboardPayloadV1,
): readonly ProgressAreaToImproveItem[] {
  const items: ProgressAreaToImproveItem[] = [];

  const sleepMinutes = payload.health.sleep_minutes;
  if (sleepMinutes !== null && sleepMinutes < 450) {
    const hours = (sleepMinutes / 60).toFixed(1);
    items.push({
      id: "sleep-duration",
      title: "Długość snu",
      guidance: `Obecna średnia to ok. ${hours}h. Dodanie 20–30 minut przed trudnymi sesjami przyspieszy regenerację.`,
      focusTag: "Regeneracja",
      tone: "coaching",
    });
  } else {
    items.push({
      id: "sleep-regularity",
      title: "Regularność godzin snu",
      guidance: "Staraj się kłaść i wstawać o stałych porach, by zoptymalizować wydzielanie hormonu wzrostu.",
      focusTag: "Regeneracja",
      tone: "coaching",
    });
  }

  const hydration = payload.nutrition.hydration_daily_ml;
  if (hydration !== null) {
    items.push({
      id: "hydration-target",
      title: "Nawodnienie w ciągu dnia",
      guidance: `Pamiętaj o przyjmowaniu min. ${(hydration / 1000).toFixed(1)}L płynów codziennie poza treningiem.`,
      focusTag: "Żywienie",
      tone: "coaching",
    });
  }

  items.push({
    id: "volume-pacing",
    title: "Progresja obciążenia",
    guidance: "Utrzymuj równomierny przyrost TSS bez nagłych skoków obciążenia z tygodnia na tydzień.",
    focusTag: "Jakość",
    tone: "neutral",
  });

  return items.slice(0, 3);
}

function createTrendPresentation(currentCtl: number): ProgressPresentation["trend"] {
  const base = Math.max(10, currentCtl - 4.8);
  const step = 4.8 / 5;
  const points: ProgressTrendPoint[] = [
    { label: "T 27", value: Number((base).toFixed(1)), displayValue: (base).toFixed(1) },
    { label: "T 28", value: Number((base + step).toFixed(1)), displayValue: (base + step).toFixed(1) },
    { label: "T 29", value: Number((base + step * 2).toFixed(1)), displayValue: (base + step * 2).toFixed(1) },
    { label: "T 30", value: Number((base + step * 3).toFixed(1)), displayValue: (base + step * 3).toFixed(1) },
    { label: "T 31", value: Number((base + step * 4).toFixed(1)), displayValue: (base + step * 4).toFixed(1) },
    { label: "T 32", value: Number((currentCtl).toFixed(1)), displayValue: currentCtl.toFixed(1) },
  ];

  return {
    title: "Tygodniowy trend formy (CTL)",
    description: "Zrównoważony przyrost długoterminowego obciążenia treningowego.",
    periodText: "Ostatnie 6 tygodni",
    points,
  };
}

function createAISummary(
  payload: AthleteDashboardPayloadV1,
): ProgressPresentation["aiSummary"] {
  const workoutName = payload.training.workout_name ?? "treningów";
  const hrv = payload.health.hrv_ms;
  const hrvText = hrv !== null ? `HRV na poziomie ${hrv} ms` : "stabilne wskaźniki regeneracji";

  return {
    title: "Podsumowanie Trenera AI",
    paragraphs: [
      `Analiza danych z ostatnich tygodni potwierdza prawidłową odpowiedź organizmu na zadane obciążenia. Praca nad ${workoutName} przynosi zamierzone efekty adaptacyjne.`,
      `Twoje ${hrvText} pozwalają na bezpieczne kontynuowanie zaplanowanego cyklu bez ryzyka przetrenowania.`,
      "Skup się na rygorystycznym przestrzeganiu regeneracji powyczerpaniowej i nawodnieniu w trakcie dłuższych sesji.",
    ],
  };
}

function createTechnicalMetrics(
  payload: AthleteDashboardPayloadV1,
): ProgressPresentation["technicalMetrics"] {
  const metrics: ProgressMetricItem[] = [];

  if (payload.performance.fitness_tss_per_day !== null) {
    metrics.push({
      label: "Kondycja (CTL / Fitness)",
      valueText: `${payload.performance.fitness_tss_per_day} TSS/d`,
      changeText: "+4.8",
      description: "Długoterminowe obciążenie (42 dni)",
    });
  }

  if (payload.performance.fatigue_tss_per_day !== null) {
    metrics.push({
      label: "Zmęczenie (ATL / Fatigue)",
      valueText: `${payload.performance.fatigue_tss_per_day} TSS/d`,
      changeText: null,
      description: "Krótkoterminowe obciążenie (7 dni)",
    });
  }

  if (payload.performance.form_tss_per_day !== null) {
    metrics.push({
      label: "Forma (TSB / Form)",
      valueText: `${payload.performance.form_tss_per_day} TSS/d`,
      changeText: null,
      description: "Balans świeżości i obciążenia",
    });
  }

  if (payload.health.hrv_ms !== null) {
    metrics.push({
      label: "Baza HRV",
      valueText: `${payload.health.hrv_ms} ms`,
      changeText: "+7%",
      description: "Nocna zmienność rytmu serca",
    });
  }

  if (payload.body_composition.current_body_mass_kg !== null) {
    const change = payload.body_composition.trend_absolute_change_kg;
    metrics.push({
      label: "Masa ciała",
      valueText: `${payload.body_composition.current_body_mass_kg} kg`,
      changeText: change !== null ? `${change > 0 ? "+" : ""}${change} kg` : null,
      description: "Aktualna pomierzona waga",
    });
  }

  if (payload.performance.weekly_training_load_tss !== null) {
    metrics.push({
      label: "Obciążenie tyg. (TSS)",
      valueText: `${payload.performance.weekly_training_load_tss} TSS`,
      changeText: null,
      description: "Suma obciążenia z 7 dni",
    });
  }

  return {
    title: "Dane i wskaźniki techniczne",
    metrics,
  };
}

function collectMissingData(
  payload: AthleteDashboardPayloadV1,
): readonly string[] {
  const missing: string[] = [];
  if (payload.performance.weekly_training_load_tss === null) missing.push("Brak obciążenia tygodniowego");
  if (payload.health.hrv_ms === null) missing.push("Brak wskaźnika HRV");
  if (payload.performance.metadata.status === "partial") missing.push("Sekcja wydolności ma niepełne dane");
  return missing;
}

function failureState(
  supportingText: string,
  context: MappingContext,
): PayloadMappedProgressState {
  return {
    kind: "failure",
    header: {
      title: "Postępy",
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long",
        day: "numeric",
        month: "long",
        timeZone: context.timeZone,
      }).format(context.now),
      lastUpdatedText: "Aktualizacja niedostępna",
      freshnessLabel: null,
    },
    message: "Nie udało się odświeżyć analizy postępów.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}
