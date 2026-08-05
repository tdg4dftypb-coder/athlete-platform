import type { ProgressPresentation } from "../models/progress-presentation";
import type { ProgressPresentationState } from "../models/progress-presentation-state";

const mockHeader = {
  title: "Postępy",
  dateText: "Poniedziałek, 3 sierpnia",
  lastUpdatedText: "Ostatnia aktualizacja: dzisiaj, 08:00",
  freshnessLabel: "Aktualne",
} as const;

export const progressPreviewData: ProgressPresentation = Object.freeze({
  source: "preview",
  header: mockHeader,
  hero: Object.freeze({
    headline: "Twoja forma systematycznie rośnie.",
    subheading: "Skutecznie adaptujesz obciążenia progowe przy zachowaniu stabilnej regeneracji.",
    trendDirection: "up",
    trendLabel: "Forma zwyżkowa",
    timeframeText: "Analiza z ostatnich 28 dni",
  }),
  improvements: Object.freeze([
    Object.freeze({
      id: "threshold-capacity",
      title: "Wytrzymałość progowa",
      description: "Zdolność do utrzymania mocy w strefie Threshold wzrosła o 12%.",
      highlightText: "+12% adaptacji",
      iconName: "activity-cycling",
    }),
    Object.freeze({
      id: "hrv-baseline",
      title: "Średnia baza HRV",
      description: "Nocna zmienność rytmu serca ustabilizowała się na wyższym poziomie.",
      highlightText: "45 ms (+7%)",
      iconName: "heart",
    }),
    Object.freeze({
      id: "body-composition",
      title: "Redukcja masy ciała",
      description: "Zgodny z planem spadek wagi bez utraty masy mięśniowej.",
      highlightText: "-1.5 kg w 4 tyg.",
      iconName: "chart",
    }),
    Object.freeze({
      id: "plan-compliance",
      title: "Zgodność z planem",
      description: "Wysoka dyscyplina w realizacji zaplanowanych jednostek akcentowych.",
      highlightText: "92% wykonania",
      iconName: "check",
    }),
  ]),
  areasToImprove: Object.freeze([
    Object.freeze({
      id: "sleep-duration",
      title: "Długość snu w tygodniu",
      guidance: "Średnia 6h 45m. Dodatkowy kwadrans snu przed dniami akcentowymi przyspieszy odbudowę mikrouszkodzeń.",
      focusTag: "Regeneracja",
      tone: "coaching",
    }),
    Object.freeze({
      id: "intra-workout-fueling",
      title: "Nawodnienie podczas sesji",
      guidance: "Przy jednostkach > 60 min pamiętaj o przyjmowaniu min. 600 ml płynów na godzinę.",
      focusTag: "Żywienie",
      tone: "coaching",
    }),
    Object.freeze({
      id: "volume-progression",
      title: "Kontrola skoków TSS",
      guidance: "Unikaj zwiększania tygodniowego obciążenia o więcej niż 15% z tygodnia na tydzień.",
      focusTag: "Jakość",
      tone: "neutral",
    }),
  ]),
  trend: Object.freeze({
    title: "Długoterminowa kondycja",
    description: "Systematyczny wzrost przewidywanej wydolności tlenowej.",
    periodText: "Ostatnie 6 tygodni",
    points: Object.freeze([
      Object.freeze({ label: "T 27", value: 24, displayValue: "24" }),
      Object.freeze({ label: "T 28", value: 25.5, displayValue: "25.5" }),
      Object.freeze({ label: "T 29", value: 26.8, displayValue: "26.8" }),
      Object.freeze({ label: "T 30", value: 27.4, displayValue: "27.4" }),
      Object.freeze({ label: "T 31", value: 28.2, displayValue: "28.2" }),
      Object.freeze({ label: "T 32", value: 28.8, displayValue: "28.8" }),
    ]),
  }),
  aiSummary: Object.freeze({
    title: "Podsumowanie Trenera AI",
    paragraphs: Object.freeze([
      "Ostatnie 4 tygodnie przyniosły widoczną poprawę adaptacji do obciążeń w strefie progowej. Twoje serce regeneruje się sprawniej, a baza HRV utrzymuje się w górnym przedziale normy.",
      "Kluczem do utrzymania tej tendencji będzie zachowanie rygoru sennego w dni poprzedzające cięższe interwały.",
      "Zgodnie z przyjętym celem redukcji masy ciała, bilans kaloryczny przynosi stabilne rezultaty przy zachowaniu pełnej mocy treningowej.",
    ]),
  }),
  technicalMetrics: Object.freeze({
    title: "Dane i wskaźniki techniczne",
    metrics: Object.freeze([
      Object.freeze({ label: "Moc progowa (FTP)", valueText: "285 W", changeText: "+10 W", description: "Szacowana moc na progu" }),
      Object.freeze({ label: "Zmienność rytmu serca (HRV)", valueText: "45.0 ms", changeText: "+7%", description: "7-dniowa średnia nocna" }),
      Object.freeze({ label: "Świeżość treningowa (TSB)", valueText: "-15.5 TSS", changeText: null, description: "Aktualny balans świeżości" }),
      Object.freeze({ label: "Krótkoterminowe obciążenie (ATL)", valueText: "44.3 TSS/d", changeText: null, description: "Obciążenie z 7 dni" }),
      Object.freeze({ label: "Długoterminowa kondycja (CTL)", valueText: "28.8 TSS/d", changeText: "+4.8", description: "Obciążenie z 42 dni" }),
      Object.freeze({ label: "Aktualna masa ciała", valueText: "80.0 kg", changeText: "-1.5 kg", description: "Waga poranna" }),
      Object.freeze({ label: "Tygodniowe obciążenie (TSS)", valueText: "310 TSS", changeText: null, description: "Suma obciążenia z 7 dni" }),
    ]),
  }),
});

export const progressPreviewStates: Readonly<Record<ProgressPresentationState["kind"], ProgressPresentationState>> = Object.freeze({
  ready: Object.freeze({
    kind: "ready",
    progress: progressPreviewData,
  }),
  partial: Object.freeze({
    kind: "partial",
    progress: progressPreviewData,
    missingData: Object.freeze(["Brak historycznego trendu wagi", "Niepełne dane obciążenia TSS"]),
    message: "Dane o postępach są częściowe. Wyświetlamy aktualnie dostępne wskaźniki.",
  }),
  unavailable: Object.freeze({
    kind: "unavailable",
    header: Object.freeze({
      title: "Postępy",
      dateText: "Brak danych",
      lastUpdatedText: "Nie można pobrać historii",
      freshnessLabel: null,
    }),
    reason: "Wymagany jest co najmniej 7-dniowy okres rejestracji treningów i regeneracji.",
    message: "Analiza postępów jest niedostępna",
    nextAction: "Kontynuuj rejestrowanie codziennych odpraw i treningów.",
  }),
  stale: Object.freeze({
    kind: "stale",
    progress: Object.freeze({
      ...progressPreviewData,
      header: Object.freeze({
        ...mockHeader,
        lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 18:30",
        freshnessLabel: "Wymaga odświeżenia",
      }),
    }),
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 18:30",
    message: "Wyświetlane dane o postępach pochodzą z poprzedniego dnia.",
  }),
  loading: Object.freeze({
    kind: "loading",
    message: "Trwa analizowanie Twoich postępów i trendów...",
  }),
  failure: Object.freeze({
    kind: "failure",
    header: Object.freeze({
      title: "Postępy",
      dateText: "Brak połączenia",
      lastUpdatedText: "Błąd pobierania",
      freshnessLabel: null,
    }),
    message: "Nie udało się odświeżyć analizy postępów.",
    supportingText: "Sprawdź połączenie z siecią i spróbuj ponownie.",
    retryLabel: "Spróbuj ponownie",
  }),
});
