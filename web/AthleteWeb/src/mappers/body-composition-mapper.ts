import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type { AthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-v1";
import type {
  BodyCompositionBreakdownItem,
  BodyCompositionDataQualityPresentation,
  BodyCompositionGoalAlignmentPresentation,
  BodyCompositionHeaderPresentation,
  BodyCompositionHeroPresentation,
  BodyCompositionKeyChangeItem,
  BodyCompositionMetricItem,
  BodyCompositionPresentation,
  BodyCompositionTrendPresentation,
} from "../models/body-composition-presentation";
import type { BodyCompositionPresentationState } from "../models/body-composition-presentation-state";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";
import type { MappingContext } from "./mapping-context";

export type PayloadMappedBodyState = Exclude<
  BodyCompositionPresentationState,
  { kind: "loading" }
>;

export function parseAndMapAthleteDashboardToBody(
  input: unknown,
  context: MappingContext,
): PayloadMappedBodyState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) {
    return failureState(
      `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
      context,
    );
  }
  return mapAthleteDashboardToBody(parsed.data, context);
}

export function mapAthleteDashboardToBody(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedBodyState {
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
    payload.body_composition.metadata.status === "unavailable" ||
    payload.body_composition.current_body_mass_kg === null
  ) {
    return {
      kind: "unavailable",
      header,
      message: "Dane o składzie ciała są niedostępne.",
      reason: "Brak zarejestrowanych pomiarów masy ciała.",
      nextAction: "Dodaj pierwszy pomiar masy ciała, aby rozpocząć śledzenie zmian.",
    };
  }

  const missingData = collectMissingData(payload);
  const body = createBodyPresentation(payload, header);

  if (stale) {
    return {
      kind: "stale",
      body,
      message: "Wyświetlane dane o składzie ciała pochodzą z poprzedniego dnia.",
      lastUpdatedText: header.lastUpdatedText,
    };
  }

  if (missingData.length > 0) {
    return {
      kind: "partial",
      body,
      message: "Część danych o składzie ciała jest niepełna.",
      missingData,
    };
  }

  return { kind: "ready", body };
}

function createHeader(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  stale: boolean,
): BodyCompositionHeaderPresentation {
  const date = parseContractDate(payload.valid_for_date);
  const asOf = parseContractTimestamp(payload.as_of);
  return {
    title: "Skład ciała",
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

function createBodyPresentation(
  payload: AthleteDashboardPayloadV1,
  header: BodyCompositionHeaderPresentation,
): BodyCompositionPresentation {
  const changeKg = payload.body_composition.trend_absolute_change_kg;
  const trendDir: "down" | "stable" | "up" =
    changeKg === null || Math.abs(changeKg) < 0.2
      ? "stable"
      : changeKg < 0
      ? "down"
      : "up";

  const hero: BodyCompositionHeroPresentation = {
    headline:
      trendDir === "down"
        ? "Masa ciała zmienia się zgodnie z planem."
        : trendDir === "up"
        ? "Obserwujemy wzrost masy ciała."
        : "Masa ciała pozostaje na stabilnym poziomie.",
    subheading:
      "Tempo zmian jest monitorowane i powiązane z Twoim aktualnym celem treningowym.",
    trendDirection: trendDir,
    trendLabel:
      trendDir === "down"
        ? "Redukcja kontrolowana"
        : trendDir === "up"
        ? "Przyrost masy"
        : "Masa stabilna",
    timeframeText: payload.body_composition.trend_period_days
      ? `Analiza z ostatnich ${payload.body_composition.trend_period_days} dni`
      : "Analiza bieżącego okresu",
    goalStatusBadgeText: payload.goal.metadata.status !== "unavailable" ? "Zgodny z celem" : "Cel nieustalony",
    goalStatusVariant: payload.goal.metadata.status !== "unavailable" ? "aligned" : "neutral",
  };

  const keyChanges = createKeyChanges(payload);
  const trend = createTrendSection(payload);
  const breakdown = createBreakdownSection(payload);
  const goalAlignment = createGoalAlignmentSection(payload);
  const dataQuality = createDataQualitySection(payload);
  const technical = createTechnicalSection(payload);

  return {
    source: "payload",
    header,
    hero,
    keyChanges,
    trend,
    breakdown,
    goalAlignment,
    dataQuality,
    placeholderNote: null,
    technical,
  };
}

function createKeyChanges(
  payload: AthleteDashboardPayloadV1,
): readonly BodyCompositionKeyChangeItem[] {
  const items: BodyCompositionKeyChangeItem[] = [];
  const comp = payload.body_composition;
  const periodText = comp.trend_period_days
    ? `ostatnie ${comp.trend_period_days} dni`
    : "bieżący okres";

  if (comp.current_body_mass_kg !== null) {
    const change = comp.trend_absolute_change_kg;
    const valueText =
      change !== null
        ? `${change > 0 ? "+" : ""}${change} kg`
        : `${comp.current_body_mass_kg} kg`;
    items.push({
      id: "body-mass",
      label: "Masa ciała",
      description: "Ogólna zmiana wagi porannej.",
      trendDirection: change === null || Math.abs(change) < 0.2 ? "stable" : change < 0 ? "down" : "up",
      valueText,
      periodText,
      qualityNote: null,
      iconName: "chart",
    });
  }

  if (comp.waist_circumference_cm !== null) {
    items.push({
      id: "waist",
      label: "Obwód talii",
      description: "Pomiar obwodu pasie.",
      trendDirection: "stable",
      valueText: `${comp.waist_circumference_cm} cm`,
      periodText,
      qualityNote: null,
      iconName: "target",
    });
  }

  if (comp.body_fat_percent !== null) {
    items.push({
      id: "body-fat",
      label: "Tkanka tłuszczowa",
      description: "Zawartość procentowa tkanki tłuszczowej.",
      trendDirection: "stable",
      valueText: `${comp.body_fat_percent}%`,
      periodText,
      qualityNote: null,
      iconName: "heart",
    });
  }

  if (comp.muscle_mass_kg !== null) {
    items.push({
      id: "muscle-mass",
      label: "Masa mięśniowa",
      description: "Szacowana masa tkanki mięśniowej.",
      trendDirection: "stable",
      valueText: `${comp.muscle_mass_kg} kg`,
      periodText,
      qualityNote: null,
      iconName: "check",
    });
  }

  return items;
}

function createTrendSection(
  payload: AthleteDashboardPayloadV1,
): BodyCompositionTrendPresentation {
  const comp = payload.body_composition;
  const currentMass = comp.current_body_mass_kg;
  const baselineMass = comp.trend_baseline_body_mass_kg;

  if (currentMass === null || baselineMass === null || comp.trend_period_days === null) {
    return {
      title: "Trend masy ciała",
      description: "Trend pojawi się po zebraniu wystarczającej historii pomiarów.",
      paceText: null,
      weeklyAverageText: currentMass !== null ? `Aktualna waga: ${currentMass} kg` : null,
      points: [],
      isAvailable: false,
      unavailableMessage: "Brak historii trendu wagi w payloadzie.",
    };
  }

  const change = comp.trend_absolute_change_kg ?? 0;
  const days = comp.trend_period_days;
  const weeklyPace = Number(((change / days) * 7).toFixed(2));
  const paceText = `${weeklyPace > 0 ? "+" : ""}${weeklyPace} kg/tydz.`;

  const p1 = Number(baselineMass.toFixed(1));
  const p6 = Number(currentMass.toFixed(1));

  return {
    title: `Trend masy ciała (${days} dni)`,
    description: "Systematyczna zmiana masy ciała w wybranym horyzoncie czasowym.",
    paceText,
    weeklyAverageText: `Aktualny pomiar: ${currentMass} kg`,
    points: [
      { label: "Start", value: p1, displayValue: String(p1) },
      { label: "Dziś", value: p6, displayValue: String(p6) },
    ],
    isAvailable: true,
    unavailableMessage: null,
  };
}

function createBreakdownSection(
  payload: AthleteDashboardPayloadV1,
): readonly BodyCompositionBreakdownItem[] {
  const items: BodyCompositionBreakdownItem[] = [];
  const comp = payload.body_composition;

  if (comp.current_body_mass_kg !== null) {
    items.push({
      label: "Masa całkowita",
      valueText: `${comp.current_body_mass_kg} kg`,
      subtext: comp.trend_absolute_change_kg !== null ? `Zmiana: ${comp.trend_absolute_change_kg} kg` : null,
      statusTag: "Pomierzono",
    });
  }

  if (comp.body_fat_percent !== null) {
    items.push({
      label: "Tkanka tłuszczowa",
      valueText: `${comp.body_fat_percent}%`,
      subtext: null,
      statusTag: "BIA",
    });
  }

  if (comp.muscle_mass_kg !== null) {
    items.push({
      label: "Masa mięśniowa",
      valueText: `${comp.muscle_mass_kg} kg`,
      subtext: null,
      statusTag: "BIA",
    });
  }

  if (comp.waist_circumference_cm !== null) {
    items.push({
      label: "Obwód talii",
      valueText: `${comp.waist_circumference_cm} cm`,
      subtext: null,
      statusTag: "Taśma",
    });
  }

  return items;
}

function createGoalAlignmentSection(
  payload: AthleteDashboardPayloadV1,
): BodyCompositionGoalAlignmentPresentation {
  const targetMass = payload.goal.target_body_mass_kg;
  const currentMass = payload.body_composition.current_body_mass_kg;

  if (targetMass === null || currentMass === null) {
    return {
      title: "Zgodność z celem",
      statusMessage: "Brak zdefiniowanego celu wagowego.",
      details: ["Zdefiniuj docelową masę ciała w ustawieniach celu."],
      alignmentVariant: "neutral",
    };
  }

  const diff = currentMass - targetMass;
  const message =
    Math.abs(diff) < 0.5
      ? "Masa ciała jest bardzo blisko docelowej."
      : diff > 0
      ? `Pozostało ${(diff).toFixed(1)} kg do celu.`
      : "Masa ciała poniżej docelowej.";

  return {
    title: "Zgodność z celem",
    statusMessage: message,
    details: [
      `Docelowa masa ciała: ${targetMass} kg`,
      `Aktualna masa ciała: ${currentMass} kg`,
    ],
    alignmentVariant: "aligned",
  };
}

function createDataQualitySection(
  payload: AthleteDashboardPayloadV1,
): BodyCompositionDataQualityPresentation {
  const meta = payload.body_composition.metadata;
  const limitations: string[] = [...meta.limitations];

  if (payload.body_composition.waist_circumference_cm === null) {
    limitations.push("Brak pomiaru obwodu talii");
  }
  if (payload.body_composition.body_fat_percent === null) {
    limitations.push("Brak pomiaru tkanki tłuszczowej");
  }
  if (payload.body_composition.muscle_mass_kg === null) {
    limitations.push("Brak pomiaru masy mięśniowej");
  }

  const isComplete = meta.status === "ready" && limitations.length === 0;
  const scorePct = meta.completeness_score !== null ? `${Math.round(meta.completeness_score * 100)}% kompletności` : "Częściowe dane";

  return {
    title: "Jakość i kompletność danych",
    completenessScoreText: scorePct,
    limitations,
    isComplete,
  };
}

function createTechnicalSection(
  payload: AthleteDashboardPayloadV1,
): BodyCompositionPresentation["technical"] {
  const metrics: BodyCompositionMetricItem[] = [];

  const comp = payload.body_composition;

  if (comp.current_body_mass_kg !== null) {
    metrics.push({ label: "Masa ciała", valueText: `${comp.current_body_mass_kg} kg`, description: "Poranny pomiar wagi" });
  }

  if (comp.body_fat_percent !== null) {
    metrics.push({ label: "Tkanka tłuszczowa (%)", valueText: `${comp.body_fat_percent}%`, description: "Zawartość tłuszczu" });
  }

  if (comp.muscle_mass_kg !== null) {
    metrics.push({ label: "Masa mięśniowa", valueText: `${comp.muscle_mass_kg} kg`, description: "Szacowana tkanka mięśniowa" });
  }

  if (comp.body_water_percent !== null) {
    metrics.push({ label: "Woda w organizmie (%)", valueText: `${comp.body_water_percent}%`, description: "Poziom nawodnienia" });
  }

  if (comp.basal_metabolic_rate_kcal !== null) {
    metrics.push({ label: "BMR (Metabolizm spoczynkowy)", valueText: `${comp.basal_metabolic_rate_kcal} kcal`, description: "Podstawowy poziom energii" });
  }

  if (comp.waist_circumference_cm !== null) {
    metrics.push({ label: "Obwód talii", valueText: `${comp.waist_circumference_cm} cm`, description: "Pomiar obwodu" });
  }

  metrics.push({ label: "Data pomiaru", valueText: payload.valid_for_date, description: "Ostatni zarejestrowany dzień" });

  return {
    title: "Dane i wskaźniki techniczne",
    metrics,
  };
}

function collectMissingData(
  payload: AthleteDashboardPayloadV1,
): readonly string[] {
  const missing: string[] = [];
  if (payload.body_composition.waist_circumference_cm === null) missing.push("Brak pomiaru obwodu talii");
  if (payload.body_composition.body_fat_percent === null) missing.push("Brak pomiaru tkanki tłuszczowej");
  if (payload.body_composition.muscle_mass_kg === null) missing.push("Brak pomiaru masy mięśniowej");
  if (payload.body_composition.metadata.status === "partial") missing.push("Sekcja składu ciała ma niepełne dane");
  return missing;
}

function failureState(
  supportingText: string,
  context: MappingContext,
): PayloadMappedBodyState {
  return {
    kind: "failure",
    header: {
      title: "Skład ciała",
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long",
        day: "numeric",
        month: "long",
        timeZone: context.timeZone,
      }).format(context.now),
      lastUpdatedText: "Aktualizacja niedostępna",
      freshnessLabel: null,
    },
    message: "Nie udało się odświeżyć analizy składu ciała.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}
