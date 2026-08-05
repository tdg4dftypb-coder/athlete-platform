import type { BiomarkersPresentation } from "./biomarkers-presentation";
import type { BiomarkersPresentationState } from "./biomarkers-presentation-state";

export const sampleBiomarkersPresentation: BiomarkersPresentation = {
  title: "Badania laboratoryjne i biomarkery",
  statusLabel: "Wszystkie biomarkery zweryfikowane",
  completenessLabel: "Kompletność danych: 100%",
  latestCollectionLabel: "Ostatnie badanie: 2026-08-01",
  attentionCount: 0,
  unresolvedCount: 0,
  limitations: [],
  summary: {
    totalReports: 2,
    activeReports: 2,
    totalObservations: 4,
    verifiedObservations: 4,
    unresolvedObservations: 0,
    possibleDuplicates: 0,
    latestCollectionDate: "2026-08-01",
  },
  categories: [
    {
      categoryCode: "iron_panel",
      displayName: "Gospodarka żelazowa",
      attentionCount: 0,
      unresolvedCount: 0,
      biomarkers: [
        {
          code: "ferritin",
          name: "Ferrytyna",
          valueLabel: "35",
          unitLabel: "µg/L",
          referenceLabel: "Norma lab: 30-200",
          collectedAtLabel: "1 sie 2026, 08:00",
          trendLabel: "Wartość stabilna",
          trendDirection: "stable",
          laboratoryFlag: null,
          verificationLabel: "Zweryfikowano",
          limitations: [],
        },
      ],
    },
    {
      categoryCode: "morphology",
      displayName: "Morfologia",
      attentionCount: 0,
      unresolvedCount: 0,
      biomarkers: [
        {
          code: "hemoglobin",
          name: "Hemoglobina",
          valueLabel: "142",
          unitLabel: "g/L",
          referenceLabel: "Norma lab: 135-175",
          collectedAtLabel: "1 sie 2026, 08:00",
          trendLabel: "Trend rosnący",
          trendDirection: "increasing",
          laboratoryFlag: null,
          verificationLabel: "Zweryfikowano",
          limitations: [],
        },
      ],
    },
  ],
  unresolvedItems: [],
};

export const samplePartialBiomarkersPresentation: BiomarkersPresentation = {
  ...sampleBiomarkersPresentation,
  statusLabel: "Częściowe dane laboratoryjne",
  completenessLabel: "Kompletność danych: 75%",
  attentionCount: 1,
  unresolvedCount: 1,
  limitations: ["1 nierozpoznane badanie wymaga przeglądu."],
  summary: {
    ...sampleBiomarkersPresentation.summary,
    totalObservations: 4,
    verifiedObservations: 3,
    unresolvedObservations: 1,
  },
  unresolvedItems: [
    {
      id: "obs-unres-preview-1",
      name: "Nierozpoznany Marker Syntetyczny",
      unit: "U/L",
      collectedAtLabel: "1 sie 2026, 08:00",
      reason: "Nierozpoznany alias biomarker w rejestrze.",
    },
  ],
};

export const biomarkersPreviewStates: Record<BiomarkersPresentationState["kind"], BiomarkersPresentationState> = {
  ready: {
    kind: "ready",
    presentation: sampleBiomarkersPresentation,
  },
  partial: {
    kind: "partial",
    presentation: samplePartialBiomarkersPresentation,
    message: "Panel biomarkerów jest dostępny, ale występują ograniczenia jakościowe danych.",
    limitations: samplePartialBiomarkersPresentation.limitations,
  },
  unavailable: {
    kind: "unavailable",
    title: "Badania laboratoryjne",
    message: "Brak aktywnych badań laboratoryjnych w profilu.",
    reason: "Nie zaimportowano jeszcze żadnych wyników badań laboratoryjnych.",
    nextAction: "Dodaj pierwsze wyniki badań, aby przejrzeć panel biomarkerów.",
  },
  stale: {
    kind: "stale",
    presentation: sampleBiomarkersPresentation,
    message: "Dane laboratoryjne mogą być nieaktualne.",
    lastUpdatedText: "Ostatnia aktualizacja: 1 sie 2026, 08:00.",
  },
  loading: {
    kind: "loading",
    message: "Wczytywanie panelu biomarkerów...",
  },
  failure: {
    kind: "failure",
    title: "Błąd pobierania danych",
    message: "Nie удалось pobrać danych biomarkerów.",
    supportingText: "Błąd połączenia z serwerem laboratoryjnym.",
    retryLabel: "Spróbuj ponownie",
  },
};
