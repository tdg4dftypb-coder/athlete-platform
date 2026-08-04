import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type { AthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-v1";
import type {
  MealTimelineItem,
  NutritionFocusItem,
  NutritionHeroPresentation,
  NutritionMetricItem,
  NutritionPresentation,
  NutritionPresentationHeader,
} from "../models/nutrition-presentation";
import type { NutritionPresentationState } from "../models/nutrition-presentation-state";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";
import type { MappingContext } from "./mapping-context";

export type PayloadMappedNutritionState = Exclude<
  NutritionPresentationState,
  { kind: "loading" }
>;

export function parseAndMapAthleteDashboardToNutrition(
  input: unknown,
  context: MappingContext,
): PayloadMappedNutritionState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) {
    return failureState(
      `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
      context,
    );
  }
  return mapAthleteDashboardToNutrition(parsed.data, context);
}

export function mapAthleteDashboardToNutrition(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedNutritionState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return failureState("Payload zawiera niespójny kontekst czasu.", context);
  }

  const stale =
    payload.valid_for_date !== dateInTimeZone(context.now, context.timeZone) ||
    ageMs > context.staleAfterMs;
  const header = createHeader(payload, context, stale);

  if (payload.nutrition.metadata.status === "unavailable") {
    return {
      kind: "unavailable",
      header,
      message: "Plan żywieniowy jest niedostępny.",
      reason: "Brak przypisanych zaleceń dietetycznych w decyzji dnia.",
      nextAction: "Sprawdź ponowną aktualizację po kolejnym rozliczeniu.",
    };
  }

  const missingData = collectMissingData(payload);
  const nutrition = createNutrition(payload, header);

  if (stale) {
    return {
      kind: "stale",
      nutrition,
      message: "Wyświetlane dane żywieniowe pochodzą z poprzedniego dnia.",
      lastUpdatedText: header.lastUpdatedText,
    };
  }

  if (missingData.length > 0) {
    return {
      kind: "partial",
      nutrition,
      message: "Część danych żywieniowych jest niepełna.",
      missingData,
    };
  }

  return { kind: "ready", nutrition };
}

function createHeader(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  stale: boolean,
): NutritionPresentationHeader {
  const date = parseContractDate(payload.valid_for_date);
  const asOf = parseContractTimestamp(payload.as_of);
  return {
    title: "Odżywianie",
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

function createNutrition(
  payload: AthleteDashboardPayloadV1,
  header: NutritionPresentationHeader,
): NutritionPresentation {
  const hasCarbsTarget = payload.nutrition.carbohydrate_target_g !== null;
  const hero: NutritionHeroPresentation = {
    headline: hasCarbsTarget
      ? "Twoje odżywianie wspiera dzisiejszy trening."
      : "Zalecenia żywieniowe dla dzisiejszego planu.",
    subheading: hasCarbsTarget
      ? "Zadbaj o podaż węglowodanów okołotreningowo dla zachowania pełnej mocy."
      : "Stosuj się do dostępnych wskazówek okołotreningowych.",
    statusBadgeText: hasCarbsTarget ? "Optymalne wsparcie" : "Wsparcie podstawowe",
    statusVariant: hasCarbsTarget ? "optimal" : "moderate",
    timeframeText: "Plan żywieniowy na dzisiaj",
  };

  const focusItems = createFocusItems(payload);
  const mealTimeline = createMealTimeline(payload);
  const hydration = createHydration(payload);
  const coachSummary = createCoachSummary(payload);
  const technical = createTechnical(payload);

  return {
    source: "payload",
    header,
    hero,
    focusItems,
    mealTimeline,
    hydration,
    coachSummary,
    technical,
  };
}

function createFocusItems(
  payload: AthleteDashboardPayloadV1,
): readonly NutritionFocusItem[] {
  const items: NutritionFocusItem[] = [];

  const proteinG = payload.nutrition.protein_target_g;
  if (proteinG !== null) {
    items.push({
      id: "protein-focus",
      title: "Podaż białka",
      status: "check",
      description: `Zaplanowano ${proteinG}g białka dla ochrony tkanki mięśniowej.`,
      highlightText: `${proteinG}g cel`,
      tagLabel: "Regeneracja",
    });
  }

  const hydrationMl = payload.nutrition.hydration_daily_ml;
  if (hydrationMl !== null) {
    items.push({
      id: "hydration-focus",
      title: "Nawodnienie dzienny cel",
      status: "check",
      description: `Docelowa objętość płynów wynosząca ${(hydrationMl / 1000).toFixed(1)}L.`,
      highlightText: `${(hydrationMl / 1000).toFixed(1)}L cel`,
      tagLabel: "Bilans",
    });
  }

  const carbsG = payload.nutrition.carbohydrate_target_g;
  if (carbsG !== null) {
    items.push({
      id: "carbs-focus",
      title: "Węglowodany okołotreningowe",
      status: "alert",
      description: `Całkowita pula węglowodanów ${carbsG}g ukierunkowana na sesję akcentową.`,
      highlightText: `${carbsG}g cel`,
      tagLabel: "Energia",
    });
  }

  return items;
}

function createMealTimeline(
  payload: AthleteDashboardPayloadV1,
): readonly MealTimelineItem[] {
  const items: MealTimelineItem[] = [];

  const preCarbs = payload.nutrition.fueling_pre_workout_carbohydrate_g;
  if (preCarbs !== null && preCarbs > 0) {
    items.push({
      id: "pre-workout",
      mealName: "Przed treningiem",
      timeText: "Przed treningiem",
      timingLabel: "Przed treningiem",
      description: "Lekko strawne węglowodany proste i woda z izotonikiem.",
      targetCarbs: `${preCarbs}g Węglowodany`,
      targetProtein: null,
    });
  }

  const duringCarbs = payload.nutrition.fueling_during_workout_carbohydrate_g_per_hour;
  if (duringCarbs !== null && duringCarbs > 0) {
    items.push({
      id: "during-workout",
      mealName: "W trakcie treningu",
      timeText: "W trakcie",
      timingLabel: "W trakcie",
      description: "Nawadnianie i uzupełnianie węglowodanów w trakcie wysiłku.",
      targetCarbs: `${duringCarbs}g/h Węglowodany`,
      targetProtein: null,
    });
  }

  const postCarbs = payload.nutrition.fueling_post_workout_carbohydrate_g;
  const postProtein = payload.nutrition.fueling_post_workout_protein_g;
  if ((postCarbs !== null && postCarbs > 0) || (postProtein !== null && postProtein > 0)) {
    items.push({
      id: "post-workout",
      mealName: "Po treningu",
      timeText: "Po treningu",
      timingLabel: "Po treningu",
      description: "Posiłek/koktajl regeneracyjny przyspieszający resyntezę glikogenu.",
      targetCarbs: postCarbs !== null ? `${postCarbs}g Węglowodany` : null,
      targetProtein: postProtein !== null ? `${postProtein}g Białko` : null,
    });
  }

  return items;
}

function createHydration(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["hydration"] {
  const target = payload.nutrition.hydration_daily_ml;

  if (target === null) {
    return {
      title: "Poziom nawodnienia",
      currentVolumeMl: 0,
      targetVolumeMl: 0,
      progressLabel: "Cel nawodnienia niedostępny",
      statusText: "Brak zdefiniowanego dziennego celu nawodnienia.",
    };
  }

  const duringWorkoutMl = payload.nutrition.hydration_during_workout_ml_per_hour;
  const subtext = duringWorkoutMl !== null
    ? `Zalecane nawodnienie w trakcie wysiłku: ${duringWorkoutMl} ml/h.`
    : `Docelowa objętość płynów: ${(target / 1000).toFixed(1)} L w ciągu dnia.`;

  return {
    title: "Poziom nawodnienia",
    currentVolumeMl: target,
    targetVolumeMl: target,
    progressLabel: `Cel dzienny: ${(target / 1000).toFixed(1)} L`,
    statusText: subtext,
  };
}

function createCoachSummary(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["coachSummary"] {
  const workoutName = payload.training.workout_name ?? "treningu";
  return {
    title: "Podsumowanie Trenera AI",
    paragraphs: [
      `Strategia żywieniowa została zsynchronizowana z wymaganiami ${workoutName}.`,
      "Zadbaj o spożycie zalecanego paliwa okołotreningowego i nawodnienie w trakcie wysiłku.",
    ],
  };
}

function createTechnical(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["technical"] {
  const metrics: NutritionMetricItem[] = [];

  if (payload.nutrition.observed_daily_expenditure_kcal !== null) {
    metrics.push({
      label: "Zaobserwowany wydatek energii",
      valueText: `${payload.nutrition.observed_daily_expenditure_kcal} kcal`,
      targetText: null,
      description: "Suma wydatku energetycznego z pomiarów",
    });
  }

  if (payload.nutrition.estimated_daily_requirement_kcal !== null) {
    metrics.push({
      label: "Szacowane zapotrzebowanie",
      valueText: `${payload.nutrition.estimated_daily_requirement_kcal} kcal`,
      targetText: null,
      description: "Szacowane zapotrzebowanie kaloryczne",
    });
  }

  if (payload.nutrition.carbohydrate_target_g !== null) {
    metrics.push({
      label: "Węglowodany",
      valueText: `${payload.nutrition.carbohydrate_target_g} g`,
      targetText: null,
      description: "Główne źródło energii",
    });
  }

  if (payload.nutrition.protein_target_g !== null) {
    metrics.push({
      label: "Białko",
      valueText: `${payload.nutrition.protein_target_g} g`,
      targetText: null,
      description: "Synteza i regeneracja tkanki",
    });
  }

  if (payload.nutrition.hydration_daily_ml !== null) {
    metrics.push({
      label: "Dzienny cel płynów",
      valueText: `${payload.nutrition.hydration_daily_ml} ml`,
      targetText: null,
      description: "Rekomendowana objętość nawodnienia",
    });
  }

  if (payload.nutrition.hydration_during_workout_ml_per_hour !== null) {
    metrics.push({
      label: "Nawodnienie w trakcie wysiłku",
      valueText: `${payload.nutrition.hydration_during_workout_ml_per_hour} ml/h`,
      targetText: null,
      description: "Płyny na godzinę treningu",
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
  if (
    payload.nutrition.estimated_daily_requirement_kcal === null &&
    payload.nutrition.observed_daily_expenditure_kcal === null
  ) {
    missing.push("Brak wartości kalorycznej");
  }
  if (payload.nutrition.carbohydrate_target_g === null) {
    missing.push("Brak wartości węglowodanów");
  }
  if (payload.nutrition.protein_target_g === null) {
    missing.push("Brak celów białka");
  }
  if (payload.nutrition.hydration_daily_ml === null) {
    missing.push("Brak celu nawodnienia");
  }
  if (payload.nutrition.metadata.status === "partial") {
    missing.push("Sekcja żywieniowa ma niepełne dane");
  }
  return missing;
}

function failureState(
  supportingText: string,
  context: MappingContext,
): PayloadMappedNutritionState {
  return {
    kind: "failure",
    header: {
      title: "Odżywianie",
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long",
        day: "numeric",
        month: "long",
        timeZone: context.timeZone,
      }).format(context.now),
      lastUpdatedText: "Aktualizacja niedostępna",
      freshnessLabel: null,
    },
    message: "Nie udało się odświeżyć widoku odżywiania.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}
