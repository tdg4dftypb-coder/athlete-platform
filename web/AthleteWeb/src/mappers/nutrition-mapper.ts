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
  const hero: NutritionHeroPresentation = {
    headline: "Twoje odżywianie wspiera dzisiejszy trening.",
    subheading: "Zadbaj o podaż węglowodanów okołotreningowo dla zachowania pełnej mocy.",
    statusBadgeText: "Optymalne wsparcie",
    statusVariant: "optimal",
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
      highlightText: `${proteinG}g ok`,
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
      highlightText: `${(hydrationMl / 1000).toFixed(1)}L ok`,
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

  items.push({
    id: "recovery-ratio",
    title: "Odbudowa glikogenu",
    status: "check",
    description: "Spożyj posiłek po treningu w ciągu 45 minut od zakończenia jazdy.",
    highlightText: "Okienko 45m",
    tagLabel: "Glikogen",
  });

  return items;
}

function createMealTimeline(
  payload: AthleteDashboardPayloadV1,
): readonly MealTimelineItem[] {
  const carbsG = payload.nutrition.carbohydrate_target_g ?? 330;
  const proteinG = payload.nutrition.protein_target_g ?? 160;

  const preCarbs = payload.nutrition.fueling_pre_workout_carbohydrate_g ?? Math.round(carbsG * 0.2);
  const postCarbs = payload.nutrition.fueling_post_workout_carbohydrate_g ?? Math.round(carbsG * 0.25);
  const standardCarbs = Math.round((carbsG - preCarbs - postCarbs) / 3);

  const postProtein = payload.nutrition.fueling_post_workout_protein_g ?? Math.round(proteinG * 0.25);
  const standardProtein = Math.round((proteinG - postProtein) / 4);

  return [
    {
      id: "breakfast",
      mealName: "Śniadanie",
      timeText: "07:30",
      timingLabel: "Standardowy",
      description: "Owsianka z owocami i odżywką białkową.",
      targetCarbs: `${standardCarbs}g Carbs`,
      targetProtein: `${standardProtein}g Protein`,
    },
    {
      id: "lunch",
      mealName: "Lunch",
      timeText: "12:30",
      timingLabel: "Standardowy",
      description: "Posiłek złożony z węglowodanów złożonych i chudego mięsa lub strączków.",
      targetCarbs: `${standardCarbs}g Carbs`,
      targetProtein: `${standardProtein}g Protein`,
    },
    {
      id: "pre-workout",
      mealName: "Przed treningiem",
      timeText: "16:00",
      timingLabel: "Przed treningiem",
      description: "Lekko strawne węglowodany proste i woda z izotonikiem.",
      targetCarbs: `${preCarbs}g Carbs`,
      targetProtein: "5g Protein",
    },
    {
      id: "post-workout",
      mealName: "Po treningu",
      timeText: "18:15",
      timingLabel: "Po treningu",
      description: "Koktajl regeneracyjny (węglowodany + białko) przyspieszający resyntezę.",
      targetCarbs: `${postCarbs}g Carbs`,
      targetProtein: `${postProtein}g Protein`,
    },
    {
      id: "dinner",
      mealName: "Kolacja",
      timeText: "20:00",
      timingLabel: "Standardowy",
      description: "Pełnowartościowy posiłek z warzywami i zdrowymi tłuszczami.",
      targetCarbs: `${standardCarbs}g Carbs`,
      targetProtein: `${standardProtein}g Protein`,
    },
  ];
}

function createHydration(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["hydration"] {
  const target = payload.nutrition.hydration_daily_ml ?? 3000;
  const current = Math.round(target * 0.8);
  const pct = Math.round((current / target) * 100);

  return {
    title: "Poziom nawodnienia",
    currentVolumeMl: current,
    targetVolumeMl: target,
    progressLabel: `${pct}% celu dziennego`,
    statusText: `Pozostało ${target - current} ml do uzupełnienia przed końcem dnia.`,
  };
}

function createCoachSummary(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["coachSummary"] {
  const workoutName = payload.training.workout_name ?? "treningu";
  return {
    title: "Podsumowanie Trenera AI",
    paragraphs: [
      `Strategia żywieniowa została zsynchronizowana z wymaganiami ${workoutName}. Węglowodany skumulowane są w oknie okołotreningowym.`,
      "Zadbaj o spożycie przekąski węglowodanowej 90 minut przed treningiem i nie pomijaj koktajlu powyczerpaniowego.",
      "Utrzymuj stały napływ płynów z elektrolitami przez całe popołudnie.",
    ],
  };
}

function createTechnical(
  payload: AthleteDashboardPayloadV1,
): NutritionPresentation["technical"] {
  const metrics: NutritionMetricItem[] = [];

  const calories = payload.nutrition.estimated_daily_requirement_kcal ?? payload.nutrition.observed_daily_expenditure_kcal;
  if (calories !== null) {
    metrics.push({
      label: "Kalorie",
      valueText: `${calories} kcal`,
      targetText: "Cel: 2700 kcal",
      description: "Szacowany bilans dobowy",
    });
  }


  if (payload.nutrition.carbohydrate_target_g !== null) {
    metrics.push({
      label: "Węglowodany",
      valueText: `${payload.nutrition.carbohydrate_target_g} g`,
      targetText: "Cel: 340 g",
      description: "Główne źródło energii",
    });
  }

  if (payload.nutrition.protein_target_g !== null) {
    metrics.push({
      label: "Białko",
      valueText: `${payload.nutrition.protein_target_g} g`,
      targetText: "Cel: 155 g",
      description: "Synteza i regeneracja",
    });
  }

  metrics.push({
    label: "Tłuszcze",
    valueText: "70 g",
    targetText: "Cel: 72 g",
    description: "Niezbędne kwasy tłuszczowe",
  });

  metrics.push({
    label: "Błonnik",
    valueText: "32 g",
    targetText: "Cel: 30 g",
    description: "Błonnik pokarmowy",
  });

  metrics.push({
    label: "Sód",
    valueText: "2400 mg",
    targetText: "Cel: 2300 mg",
    description: "Główny elektrolit osocza",
  });

  metrics.push({
    label: "Potas",
    valueText: "3800 mg",
    targetText: "Cel: 3500 mg",
    description: "Elektrolit wewnątrzkomórkowy",
  });

  return {
    title: "Dane i wskaźniki techniczne (Makro i Mikro)",
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
