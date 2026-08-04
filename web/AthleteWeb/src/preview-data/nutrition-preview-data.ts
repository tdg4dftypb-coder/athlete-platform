import type { NutritionPresentation } from "../models/nutrition-presentation";
import type { NutritionPresentationState } from "../models/nutrition-presentation-state";

const mockHeader = {
  title: "Odżywianie",
  dateText: "Poniedziałek, 3 sierpnia",
  lastUpdatedText: "Ostatnia aktualizacja: dzisiaj, 08:00",
  freshnessLabel: "Aktualne",
} as const;

export const nutritionPreviewData: NutritionPresentation = Object.freeze({
  source: "preview",
  header: mockHeader,
  hero: Object.freeze({
    headline: "Twoje odżywianie wspiera dzisiejszy trening.",
    subheading: "Strategiczna dostępność węglowodanów w oknie okołotreningowym zapewnia optymalną moc na progu.",
    statusBadgeText: "Optymalne wsparcie",
    statusVariant: "optimal",
    timeframeText: "Plan żywieniowy na dzisiaj",
  }),
  focusItems: Object.freeze([
    Object.freeze({
      id: "protein-distribution",
      title: "Podaż białka",
      status: "check",
      description: "Równomierny rozkład aminokwasów co 3–4 godziny stymuluje syntezę białek mięśniowych.",
      highlightText: "160g ok",
      tagLabel: "Regeneracja",
    }),
    Object.freeze({
      id: "hydration-target",
      title: "Nawodnienie",
      status: "check",
      description: "3.0L płynów z elektrolitami zapobiega spadkowi objętości osocza w trakcie wysiłku.",
      highlightText: "3.0L ok",
      tagLabel: "Bilans",
    }),
    Object.freeze({
      id: "pre-workout-carbs",
      title: "Węglowodany przed treningiem",
      status: "alert",
      description: "Zjedz 60g łatwo przyswajalnych węglowodanów na 90 min przed sesją Próg 45.",
      highlightText: "60g przed sesją",
      tagLabel: "Energia",
    }),
    Object.freeze({
      id: "post-workout-recovery",
      title: "Odbudowa glikogenu",
      status: "check",
      description: "Posiłek powyczerpaniowy z węglowodanami i białkiem w relacji 3:1.",
      highlightText: "3:1 ok",
      tagLabel: "Glikogen",
    }),
  ]),
  mealTimeline: Object.freeze([
    Object.freeze({
      id: "breakfast",
      mealName: "Śniadanie",
      timeText: "07:30",
      timingLabel: "Standardowy",
      description: "Owsianka na napoju migdałowym z jagodami, orzechami i odżywką białkową.",
      targetCarbs: "50g Carbs",
      targetProtein: "30g Protein",
    }),
    Object.freeze({
      id: "lunch",
      mealName: "Lunch",
      timeText: "12:30",
      timingLabel: "Standardowy",
      description: "Ryż basmati z pieczonym kurczakiem i warzywami na parze.",
      targetCarbs: "70g Carbs",
      targetProtein: "40g Protein",
    }),
    Object.freeze({
      id: "pre-workout",
      mealName: "Przed treningiem",
      timeText: "16:00",
      timingLabel: "Przed treningiem",
      description: "Banan, wafel ryżowy z miodem oraz szklanka wody z dodatkiem izotoniku.",
      targetCarbs: "60g Carbs",
      targetProtein: "5g Protein",
    }),
    Object.freeze({
      id: "post-workout",
      mealName: "Po treningu",
      timeText: "18:15",
      timingLabel: "Po treningu",
      description: "Koktajl regeneracyjny (białko serwatkowe + banan + napój owsiany).",
      targetCarbs: "45g Carbs",
      targetProtein: "35g Protein",
    }),
    Object.freeze({
      id: "dinner",
      mealName: "Kolacja",
      timeText: "20:00",
      timingLabel: "Standardowy",
      description: "Pieczony łosoś z komosą ryżową i dużą porcją zielonych warzyw.",
      targetCarbs: "35g Carbs",
      targetProtein: "35g Protein",
    }),
  ]),
  hydration: Object.freeze({
    title: "Poziom nawodnienia",
    currentVolumeMl: 2400,
    targetVolumeMl: 3000,
    progressLabel: "80% celu dziennego",
    statusText: "Pozostało 600 ml do uzupełnienia przed wieczorem.",
  }),
  coachSummary: Object.freeze({
    title: "Podsumowanie Trenera AI",
    paragraphs: Object.freeze([
      "Twój dzisiejszy plan żywieniowy jest idealnie dopasowany do akcentu progowego w Strefie 4. Odpowiednie nasycenie glikogenem ułatwi utrzymanie mocy tlenowej.",
      "Pamiętaj o przyjęciu lekkich węglowodanów na 90 minut przed treningiem, by uniknąć spadków poziomu cukru we krwi w trakcie pierwszej serii interwałów.",
      "Po zakończeniu jazdy skoncentruj się na szybkiej resyntezie glikogenu i nawodnieniu z elektrolitami.",
    ]),
  }),
  technical: Object.freeze({
    title: "Dane i wskaźniki techniczne (Makro i Mikro)",
    metrics: Object.freeze([
      Object.freeze({ label: "Energia (Kalorie)", valueText: "2650 kcal", targetText: "Cel: 2700 kcal", description: "Szacowane dzienne zapotrzebowanie" }),
      Object.freeze({ label: "Węglowodany", valueText: "330 g", targetText: "Cel: 340 g", description: "Główne paliwo dla Strefy 4" }),
      Object.freeze({ label: "Białko", valueText: "160 g", targetText: "Cel: 155 g", description: "Ochrona i synteza włókien" }),
      Object.freeze({ label: "Tłuszcze", valueText: "70 g", targetText: "Cel: 72 g", description: "Wsparcie hormonalne" }),
      Object.freeze({ label: "Błonnik", valueText: "32 g", targetText: "Cel: 30 g", description: "Zdrowie mikrobiomu" }),
      Object.freeze({ label: "Sód", valueText: "2400 mg", targetText: "Cel: 2300 mg", description: "Równowaga osmotyczna" }),
      Object.freeze({ label: "Potas", valueText: "3800 mg", targetText: "Cel: 3500 mg", description: "Przewodnictwo nerwowo-mięśniowe" }),
    ]),
  }),
});

export const nutritionPreviewStates: Readonly<Record<NutritionPresentationState["kind"], NutritionPresentationState>> = Object.freeze({
  ready: Object.freeze({
    kind: "ready",
    nutrition: nutritionPreviewData,
  }),
  partial: Object.freeze({
    kind: "partial",
    nutrition: nutritionPreviewData,
    missingData: Object.freeze(["Brak szczegółowego podziału mikroskładników", "Niepełny rejestr nawodnienia"]),
    message: "Część danych żywieniowych jest niepełna. Wyświetlamy aktualnie dostępne wskaźniki.",
  }),
  unavailable: Object.freeze({
    kind: "unavailable",
    header: Object.freeze({
      title: "Odżywianie",
      dateText: "Brak danych",
      lastUpdatedText: "Nie można pobrać planu żywieniowego",
      freshnessLabel: null,
    }),
    reason: "Wymagany jest przypisany cel i podsumowanie żywieniowe dla dzisiejszego treningu.",
    message: "Plan żywieniowy jest niedostępny",
    nextAction: "Sprawdź po kolejnej aktualizacji danych.",
  }),
  stale: Object.freeze({
    kind: "stale",
    nutrition: Object.freeze({
      ...nutritionPreviewData,
      header: Object.freeze({
        ...mockHeader,
        lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 19:15",
        freshnessLabel: "Wymaga odświeżenia",
      }),
    }),
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 19:15",
    message: "Wyświetlane dane żywieniowe pochodzą z poprzedniego dnia.",
  }),
  loading: Object.freeze({
    kind: "loading",
    message: "Trwa dopasowywanie strategii żywieniowej do dzisiejszego treningu...",
  }),
  failure: Object.freeze({
    kind: "failure",
    header: Object.freeze({
      title: "Odżywianie",
      dateText: "Brak połączenia",
      lastUpdatedText: "Błąd pobierania",
      freshnessLabel: null,
    }),
    message: "Nie udało się odświeżyć widoku odżywiania.",
    supportingText: "Sprawdź połączenie z siecią i spróbuj ponownie.",
    retryLabel: "Spróbuj ponownie",
  }),
});
