import type { RecoveryPresentation } from "../models/recovery-presentation";
import type {
  RecoveryPresentationState,
  RecoveryStateKind,
} from "../models/recovery-presentation-state";

const previewHeader = Object.freeze({
  title: "Regeneracja",
  dateText: "poniedziałek, 3 sierpnia",
  lastUpdatedText: "Ostatnia aktualizacja: 3 sierpnia, 07:30",
  freshnessLabel: "Aktualne",
});

export const recoveryPreviewData: RecoveryPresentation = Object.freeze({
  source: "preview",
  header: previewHeader,
  hero: Object.freeze({
    statusLabel: "Dobra regeneracja",
    narrative: "Organizm dobrze odpowiedział na spokojniejsze dni. Dzisiejsza ocena wspiera realizację zaplanowanego treningu.",
    score: 84,
    scoreLabel: "Recovery Score",
    tone: "positive",
  }),
  factors: Object.freeze([
    Object.freeze({
      id: "hrv",
      label: "HRV",
      statusLabel: "W indywidualnej normie",
      valueText: "45 ms",
      contextText: "Dzisiejszy pomiar",
      description: "Zmienność rytmu serca wróciła do Twojego zwykłego zakresu.",
      trendText: "+7% względem wczoraj",
      tone: "positive",
    }),
    Object.freeze({
      id: "sleep",
      label: "Sen",
      statusLabel: "Dobra jakość",
      valueText: "7 godz. 32 min",
      contextText: "Ocena snu: 91/100",
      description: "Dłuższy sen wspiera dzisiejszą gotowość do wysiłku.",
      trendText: "+1 godz. 17 min względem wczoraj",
      tone: "positive",
    }),
    Object.freeze({
      id: "resting-heart-rate",
      label: "Tętno spoczynkowe",
      statusLabel: "Stabilne",
      valueText: "51 ud./min",
      contextText: "Dzisiejszy pomiar",
      description: "Tętno spoczynkowe nie wskazuje na dodatkowe obciążenie.",
      trendText: "Bez istotnej zmiany",
      tone: "positive",
    }),
    Object.freeze({
      id: "fatigue",
      label: "Zmęczenie",
      statusLabel: "Niższe",
      valueText: "44,3 TSS/d",
      contextText: "Bieżące obciążenie",
      description: "Zmęczenie spadło po dwóch spokojniejszych dniach.",
      trendText: "Spadek o 18%",
      tone: "positive",
    }),
  ]),
  interpretation: "Regeneracja wspiera dzisiejszy trening jakościowy. Największą wartość przyniesie jakość, nie dodatkowa objętość.",
  details: Object.freeze([
    Object.freeze({
      id: "respiratory-rate",
      label: "Częstość oddechu",
      valueText: "14,2 /min",
      description: "W zakresie typowym dla ostatnich pomiarów.",
    }),
    Object.freeze({
      id: "oxygen-saturation",
      label: "Saturacja",
      valueText: "98%",
      description: "Dzisiejszy pomiar nocny.",
    }),
  ]),
  trendSummary: "HRV, sen i zmęczenie zmieniły się dziś w korzystnym kierunku.",
});

const partialRecovery: RecoveryPresentation = Object.freeze({
  ...recoveryPreviewData,
  hero: Object.freeze({
    statusLabel: "Ocena częściowa",
    narrative: "Dostępne pomiary pozwalają pokazać część obrazu, ale brakuje HRV i pełnej oceny snu.",
    score: 68,
    scoreLabel: "Recovery Score",
    tone: "caution",
  }),
  factors: Object.freeze(recoveryPreviewData.factors.map((factor) =>
    factor.id === "hrv"
      ? Object.freeze({
          ...factor,
          statusLabel: "Brak danych",
          valueText: null,
          contextText: null,
          description: "Dzisiejszy pomiar HRV nie jest dostępny.",
          trendText: null,
          tone: "neutral" as const,
        })
      : factor.id === "sleep"
        ? Object.freeze({
            ...factor,
            statusLabel: "Dane częściowe",
            contextText: null,
            description: "Czas snu jest dostępny, ale brakuje pełnej oceny jakości.",
            trendText: null,
            tone: "caution" as const,
          })
        : factor,
  )),
  interpretation: "Ograniczona kompletność danych zwiększa niepewność oceny. Dzisiejszy plan pozostaje bez zmian.",
  trendSummary: null,
});

export const recoveryPreviewStates: Readonly<
  Record<RecoveryStateKind, RecoveryPresentationState>
> = Object.freeze({
  ready: Object.freeze({ kind: "ready", recovery: recoveryPreviewData }),
  partial: Object.freeze({
    kind: "partial",
    recovery: partialRecovery,
    message: "Ocena jest dostępna, ale część czynników ma niepełne dane.",
    missingData: Object.freeze(["Brak HRV", "Brak pełnej oceny snu"]),
  }),
  unavailable: Object.freeze({
    kind: "unavailable",
    header: previewHeader,
    message: "Ocena regeneracji nie jest teraz dostępna.",
    reason: "Brakuje aktualnych danych HRV, snu i tętna spoczynkowego.",
    nextAction: "Sprawdź ponownie po kolejnej synchronizacji danych.",
  }),
  stale: Object.freeze({
    kind: "stale",
    recovery: Object.freeze({
      ...recoveryPreviewData,
      header: Object.freeze({
        ...previewHeader,
        lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 21:45",
        freshnessLabel: "Dane nieaktualne",
      }),
    }),
    message: "Ta ocena może nie opisywać dzisiejszego stanu.",
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 21:45",
  }),
  loading: Object.freeze({
    kind: "loading",
    message: "Przygotowujemy widok regeneracji.",
  }),
  failure: Object.freeze({
    kind: "failure",
    header: previewHeader,
    message: "Nie udało się teraz odświeżyć regeneracji.",
    supportingText: "Twoje dane są bezpieczne. Możesz spróbować ponownie za chwilę.",
    retryLabel: "Spróbuj ponownie",
  }),
});
