import type { TrainingPresentationHeader } from "../models/training-presentation";
import type {
  TrainingPresentationState,
  TrainingStateKind,
} from "../models/training-presentation-state";

const mockHeader: TrainingPresentationHeader = {
  title: "Trening",
  dateText: "Poniedziałek, 3 sierpnia",
  lastUpdatedText: "Ostatnia aktualizacja: dzisiaj, 08:00",
  freshnessLabel: "Aktualne",
};

export const trainingPreviewStates: Readonly<
  Record<TrainingStateKind, TrainingPresentationState>
> = {
  ready: {
    kind: "ready",
    training: {
      source: "preview",
      header: mockHeader,
      hero: {
        activityIcon: "activity-indoor-cycling",
        title: "Threshold 45 (Zwift)",
        description: "Jazda z akcentem na pracę w strefie progu beztlenowego na trenażerze stacjonarnym.",
        durationText: "45 min",
        intensityText: "Próg (Strefa 4)",
        targetGoalText: "Zwiększenie mocy na progu FTP",
      },
      objective: "Dzisiaj budujemy wytrzymałość progową i sprawność krążeniowo-oddechową przy stabilnej kadencji.",
      structure: [
        {
          id: "warmup",
          name: "Rozgrzewka",
          durationText: "10 min",
          intensityText: "Strefa 1–2",
          description: "Swobodne kręcenie, narastająca kadencja (85 → 100 RPM) z dwoma 15-sekundowymi przyśpieszeniami.",
        },
        {
          id: "main-work",
          name: "Część główna (3 × 8 min Tempo / Próg)",
          durationText: "27 min",
          intensityText: "Strefa 4 (95–100% FTP)",
          description: "3 powtórzenia po 8 minut na progu FTP z przerwą 3 minuty w Strefie 1 (luźne kręcenie).",
        },
        {
          id: "cooldown",
          name: "Schłodzenie",
          durationText: "8 min",
          intensityText: "Strefa 1",
          description: "Spokojne wyciszenie organizmu, powrót tętna do normy spoczynkowej.",
        },
      ],
      notes: [
        "Utrzymuj równą kadencję 90–95 RPM w trakcie powtórzeń progowych.",
        "Kontroluj oddech i nie zaczynaj pierwszego powtórzenia powyżej zadanej mocy.",
        "Pij napój izotoniczny regularnie co 10–15 minut.",
        "Zachowaj rezerwę sił na trzecie, ostatnie powtórzenie.",
      ],
      expectedOutcome:
        "Po treningu powinieneś czuć umiarkowane zmęczenie nóg, ale bez uczucia głębokiego wyczerpania. Trening stymuluje adaptacje krążeniowo-oddechowe bez przeładowania układu nerwowego.",
      technicalDetails: {
        intensityFactor: "0.85 IF",
        tss: "54 TSS",
        np: "245 W",
        duration: "45 min",
        estimatedEnergy: "520 kcal",
      },
    },
  },

  partial: {
    kind: "partial",
    message: "Plan treningowy jest dostępny, ale brakuje części parametrów technicznych.",
    missingData: ["Brak przewidywanego IF", "Brak dokładnej struktury bloków"],
    training: {
      source: "preview",
      header: {
        ...mockHeader,
        freshnessLabel: "Dane niepełne",
      },
      hero: {
        activityIcon: "activity-cycling",
        title: "Endurance 60",
        description: "Tlenowa jazda wytrzymałościowa w Strefie 2.",
        durationText: "60 min",
        intensityText: "Wytrzymałość (Strefa 2)",
        targetGoalText: "Budowanie bazy tlenowej",
      },
      objective: "Dzisiaj budujemy ogólną wydolność tlenową i efektywność spalania tłuszczu.",
      structure: [
        {
          id: "main-endurance",
          name: "Jazda ciągła w Strefie 2",
          durationText: "60 min",
          intensityText: "Strefa 2 (65–75% FTP)",
          description: "Równomierne tempo bez gwałtownych skoków mocy.",
        },
      ],
      notes: [
        "Jazda w konwersacyjnym tempie.",
        "Zdbaj o prawidłowe nawodnienie.",
      ],
      expectedOutcome:
        "Lekkie zmęczenie tlenowe. Trening przyspiesza regenerację po wcześniejszym mocniejszym akcencie.",
      technicalDetails: {
        intensityFactor: null,
        tss: "42 TSS",
        np: null,
        duration: "60 min",
        estimatedEnergy: "480 kcal",
      },
    },
  },

  unavailable: {
    kind: "unavailable",
    header: {
      ...mockHeader,
      freshnessLabel: "Brak planu",
    },
    message: "Na dzisiaj nie zaplanowano treningu strukturalnego.",
    reason: "W planie uwzględniono dzień pełnej regeneracji po bloku obciążeniowym.",
    nextAction: "Sprawdź odprawę jutro rano o 08:00.",
  },

  stale: {
    kind: "stale",
    message: "Plan treningowy pochodzi z wczorajszej synchronizacji i wymaga odświeżenia.",
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 18:30",
    training: {
      source: "preview",
      header: {
        ...mockHeader,
        freshnessLabel: "Dane nieaktualne",
        lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 18:30",
      },
      hero: {
        activityIcon: "activity-indoor-cycling",
        title: "Threshold 45 (Zwift)",
        description: "Poprzednio wygenerowany plan treningu progowego.",
        durationText: "45 min",
        intensityText: "Próg (Strefa 4)",
        targetGoalText: "Zwiększenie mocy na progu FTP",
      },
      objective: "Wymaga ponownej weryfikacji ze świeżymi danymi regeneracji.",
      structure: [
        {
          id: "warmup",
          name: "Rozgrzewka",
          durationText: "10 min",
          intensityText: "Strefa 1–2",
          description: "Swobodne kręcenie.",
        },
        {
          id: "main-work",
          name: "Część główna (3 × 8 min Tempo)",
          durationText: "27 min",
          intensityText: "Strefa 4",
          description: "Powtórzenia progowe.",
        },
      ],
      notes: ["Odśwież dane przed rozpoczęciem treningu."],
      expectedOutcome: "Trening z wczorajszej sesji planistycznej.",
      technicalDetails: {
        intensityFactor: "0.85 IF",
        tss: "54 TSS",
        np: "245 W",
        duration: "45 min",
        estimatedEnergy: "520 kcal",
      },
    },
  },

  loading: {
    kind: "loading",
    message: "Trwa przygotowywanie szczegółów planu treningowego...",
  },

  failure: {
    kind: "failure",
    header: {
      ...mockHeader,
      freshnessLabel: null,
      lastUpdatedText: "Aktualizacja niedostępna",
    },
    message: "Nie udało się wczytać planu treningowego.",
    supportingText: "Wystąpił problem podczas pobierania danych planisty.",
    retryLabel: "Spróbuj ponownie",
  },
};
