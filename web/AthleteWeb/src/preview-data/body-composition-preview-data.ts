import type { BodyCompositionPresentation } from "../models/body-composition-presentation";
import type { BodyCompositionPresentationState } from "../models/body-composition-presentation-state";

const mockHeader = {
  title: "Skład ciała",
  dateText: "Poniedziałek, 3 sierpnia",
  lastUpdatedText: "Ostatnia aktualizacja: dzisiaj, 08:00",
  freshnessLabel: "Aktualne",
} as const;

export const bodyCompositionPreviewData: BodyCompositionPresentation = Object.freeze({
  source: "preview",
  header: mockHeader,
  hero: Object.freeze({
    headline: "Masa ciała zmienia się zgodnie z planem.",
    subheading: "Tempo redukcji pozostaje umiarkowane, a dostępne dane nie wskazują na istotną utratę masy mięśniowej.",
    trendDirection: "down",
    trendLabel: "Redukcja kontrolowana",
    timeframeText: "Analiza z ostatnich 28 dni",
    goalStatusBadgeText: "Zgodny z celem",
    goalStatusVariant: "aligned",
  }),
  keyChanges: Object.freeze([
    Object.freeze({
      id: "body-mass",
      label: "Masa ciała",
      description: "Spadek masy ciała bez zakłóceń wydolności i spadku mocy na progu.",
      trendDirection: "down",
      valueText: "-1.5 kg",
      periodText: "ostatnie 28 dni",
      qualityNote: "Wysoka dokładność (codzienny pomiar)",
      iconName: "chart",
    }),
    Object.freeze({
      id: "waist-circumference",
      label: "Obwód talii",
      description: "Widoczna redukcja obwodu pasie świadcząca o utracie tłuszczu wisceralnego.",
      trendDirection: "down",
      valueText: "-2.0 cm",
      periodText: "ostatnie 28 dni",
      qualityNote: "Pomiar cotygodniowy",
      iconName: "target",
    }),
    Object.freeze({
      id: "body-fat",
      label: "Tkanka tłuszczowa",
      description: "Procentowa zawartość tłuszczu wykazuje stałą tendencję spadkową.",
      trendDirection: "down",
      valueText: "-1.2%",
      periodText: "ostatnie 28 dni",
      qualityNote: "Analiza bioimpedancji BIA",
      iconName: "heart",
    }),
    Object.freeze({
      id: "muscle-mass",
      label: "Masa mięśniowa",
      description: "Czysta masa mięśniowa utrzymuje się na stabilnym poziomie.",
      trendDirection: "stable",
      valueText: "61.0 kg (0.0 kg)",
      periodText: "ostatnie 28 dni",
      qualityNote: "Ochrona tkanki mięśniowej",
      iconName: "check",
    }),
  ]),
  trend: Object.freeze({
    title: "Trend masy ciała (28 dni)",
    description: "Zrównoważone tempo spadku bez nagłych skoków wagi.",
    paceText: "-0.38 kg/tydz.",
    weeklyAverageText: "Średnia z tego tygodnia: 80.0 kg",
    points: Object.freeze([
      Object.freeze({ label: "T-5", value: 81.5, displayValue: "81.5" }),
      Object.freeze({ label: "T-4", value: 81.1, displayValue: "81.1" }),
      Object.freeze({ label: "T-3", value: 80.8, displayValue: "80.8" }),
      Object.freeze({ label: "T-2", value: 80.4, displayValue: "80.4" }),
      Object.freeze({ label: "T-1", value: 80.2, displayValue: "80.2" }),
      Object.freeze({ label: "Dziś", value: 80.0, displayValue: "80.0" }),
    ]),
    isAvailable: true,
    unavailableMessage: null,
  }),
  breakdown: Object.freeze([
    Object.freeze({ label: "Masa całkowita", valueText: "80.0 kg", subtext: "Spadek o 1.5 kg", statusTag: "W normie" }),
    Object.freeze({ label: "Tkanka tłuszczowa", valueText: "17.0%", subtext: "Spadek o 1.2%", statusTag: "Optymalnie" }),
    Object.freeze({ label: "Masa mięśniowa", valueText: "61.0 kg", subtext: "Stabilna", statusTag: "Ochrona ok" }),
    Object.freeze({ label: "Obwód talii", valueText: "82 cm", subtext: "-2 cm w 28 dni", statusTag: "Redukcja" }),
  ]),
  goalAlignment: Object.freeze({
    title: "Zgodność z celem",
    statusMessage: "Tempo redukcji jest zgodne z założeniem.",
    details: Object.freeze([
      "Docelowa masa ciała: 77.0 kg",
      "Średnie tempo redukcji: -0.38 kg na tydzień (zalecane: 0.3–0.5 kg/tydzień)",
      "Brak oznak drastycznego niedoboru kalorycznego lub osłabienia mocy",
    ]),
    alignmentVariant: "aligned",
  }),
  dataQuality: Object.freeze({
    title: "Jakość i kompletność danych",
    completenessScoreText: "100% kompletności",
    limitations: Object.freeze([]),
    isComplete: true,
  }),
  placeholderNote: null,
  technical: Object.freeze({
    title: "Dane i wskaźniki techniczne",
    metrics: Object.freeze([
      Object.freeze({ label: "Masa ciała", valueText: "80.0 kg", description: "Ostatni pomiar poranny" }),
      Object.freeze({ label: "Tkanka tłuszczowa (%)", valueText: "17.0%", description: "Szacunek BIA" }),
      Object.freeze({ label: "Masa mięśniowa", valueText: "61.0 kg", description: "Czysta tkanka mięśniowa" }),
      Object.freeze({ label: "Wskaźnik BMI", valueText: "24.2 kg/m²", description: "Body Mass Index (dane techniczne)" }),
      Object.freeze({ label: "Woda w organizmie (%)", valueText: "55.0%", description: "Poziom nawodnienia tkanek" }),
      Object.freeze({ label: "BMR (Metabolizm bazowy)", valueText: "1750 kcal", description: "Podstawowe zapotrzebowanie" }),
      Object.freeze({ label: "Obwód talii", valueText: "82 cm", description: "Pomiar taśmą" }),
      Object.freeze({ label: "Data pomiaru", valueText: "2026-08-03", description: "Ostatnia aktualizacja" }),
    ]),
  }),
});

export const bodyCompositionPreviewStates: Readonly<Record<BodyCompositionPresentationState["kind"], BodyCompositionPresentationState>> = Object.freeze({
  ready: Object.freeze({
    kind: "ready",
    body: bodyCompositionPreviewData,
  }),
  partial: Object.freeze({
    kind: "partial",
    body: Object.freeze({
      ...bodyCompositionPreviewData,
      dataQuality: Object.freeze({
        title: "Jakość i kompletność danych",
        completenessScoreText: "50% kompletności",
        limitations: Object.freeze([
          "Brak pomiaru obwodu talii z ostatnich 28 dni",
          "Nieregularne ważenie poranne (rzadziej niż 3 razy w tygodniu)",
        ]),
        isComplete: false,
      }),
    }),
    missingData: Object.freeze(["Brak pomiaru obwodu talii", "Nieregularne pomiary wagi"]),
    message: "Dane o składzie ciała są częściowe. Niektóre wskaźniki zostały pominięte.",
  }),
  unavailable: Object.freeze({
    kind: "unavailable",
    header: Object.freeze({
      title: "Skład ciała",
      dateText: "Brak danych",
      lastUpdatedText: "Brak wpisów pomiarowych",
      freshnessLabel: null,
    }),
    reason: "Wymagany jest co najmniej jeden pomiar masy ciała z ostatnich 28 dni.",
    message: "Dane o składzie ciała są niedostępne",
    nextAction: "Zarejestruj pierwszy pomiar wagi porannej.",
  }),
  stale: Object.freeze({
    kind: "stale",
    body: Object.freeze({
      ...bodyCompositionPreviewData,
      header: Object.freeze({
        ...mockHeader,
        lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 19:00",
        freshnessLabel: "Wymaga odświeżenia",
      }),
    }),
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 19:00",
    message: "Wyświetlane dane o składzie ciała pochodzą z poprzedniego dnia.",
  }),
  loading: Object.freeze({
    kind: "loading",
    message: "Trwa analiza składu ciała i ocena trendu...",
  }),
  failure: Object.freeze({
    kind: "failure",
    header: Object.freeze({
      title: "Skład ciała",
      dateText: "Brak połączenia",
      lastUpdatedText: "Błąd pobierania",
      freshnessLabel: null,
    }),
    message: "Nie udało się odświeżyć analizy składu ciała.",
    supportingText: "Sprawdź połączenie z siecią i spróbuj ponownie.",
    retryLabel: "Spróbuj ponownie",
  }),
});
