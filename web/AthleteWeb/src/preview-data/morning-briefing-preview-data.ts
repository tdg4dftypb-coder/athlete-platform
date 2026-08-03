import type { MorningBriefingPresentation } from "../models/morning-briefing-presentation";
import type {
  MorningBriefingPresentationState,
  MorningBriefingStateKind,
} from "../models/morning-briefing-presentation-state";

export const morningBriefingPreviewData: MorningBriefingPresentation = Object.freeze({
  greeting: "Dzień dobry",
  athleteName: "Marcin",
  dateText: "Poniedziałek, 3 sierpnia",
  timeText: "07:30",
  coachMessage: Object.freeze([
    "Dzień zapowiada się bardzo dobrze.",
    "Po dwóch dniach spokojniejszego treningu organizm dobrze się zregenerował.",
    "Dzisiaj warto wykonać trening progowy.",
    "Największą korzyść przyniesie jakość, nie objętość.",
  ]),
  decision: Object.freeze({
    title: "Trening progowy",
    duration: "60–75 minut",
    intensity: "Strefa 3–4",
  }),
  reasons: Object.freeze([
    "HRV wróciło do normy",
    "Sen był lepszy niż zwykle",
    "Zmęczenie spadło",
  ]),
  changesSinceYesterday: Object.freeze([
    "HRV poprawiło się",
    "Sen był dłuższy",
    "Zmęczenie jest niższe",
  ]),
  todayPlan: Object.freeze([
    "Trening progowy",
    "80 g węglowodanów przed treningiem",
    "Sen przed 23:00",
  ]),
  goal: Object.freeze({
    title: "Budowa wydolności",
    progressAccessibilityLabel: "Postęp celu",
    progressLabel: "75%",
    progressValue: 0.75,
    timeline: "Tydzień 3 z 12",
  }),
  shortcuts: Object.freeze([
    Object.freeze({ id: "recovery", label: "Regeneracja" }),
    Object.freeze({ id: "training", label: "Trening" }),
    Object.freeze({ id: "nutrition", label: "Odżywianie" }),
    Object.freeze({ id: "history", label: "Historia" }),
  ]),
});

const previewHeader = Object.freeze({
  greeting: morningBriefingPreviewData.greeting,
  athleteName: morningBriefingPreviewData.athleteName,
  dateText: morningBriefingPreviewData.dateText,
  timeText: morningBriefingPreviewData.timeText,
});

const partialBriefing: MorningBriefingPresentation = Object.freeze({
  ...morningBriefingPreviewData,
  coachMessage: Object.freeze([
    "Dzisiejszy plan jest dostępny.",
    "Ocena regeneracji opiera się dziś na niepełnych danych.",
    "Najbezpieczniejszym wyborem pozostaje spokojnie kontrolowany trening progowy.",
  ]),
  reasons: Object.freeze(["Zmęczenie spadło"]),
  changesSinceYesterday: Object.freeze(["Zmęczenie jest niższe"]),
});

export const morningBriefingPreviewStates: Readonly<
  Record<MorningBriefingStateKind, MorningBriefingPresentationState>
> = Object.freeze({
  ready: Object.freeze({
    kind: "ready",
    briefing: morningBriefingPreviewData,
  }),
  partial: Object.freeze({
    kind: "partial",
    briefing: partialBriefing,
    message: "Dzisiejszy plan jest dostępny, ale ocena regeneracji opiera się na niepełnych danych.",
    missingData: Object.freeze(["Brak HRV", "Brak danych snu"]),
  }),
  unavailable: Object.freeze({
    kind: "unavailable",
    header: previewHeader,
    message: "Nie mamy dziś wystarczających danych, aby przygotować wiarygodny briefing.",
    reason: "Brakuje aktualnych danych HRV, snu i obciążenia treningowego.",
    nextAction: "Sprawdź ponownie po kolejnej synchronizacji danych.",
  }),
  stale: Object.freeze({
    kind: "stale",
    briefing: morningBriefingPreviewData,
    message: "To podsumowanie opiera się na danych z wczoraj.",
    lastUpdatedText: "Ostatnia aktualizacja: wczoraj, 21:45",
  }),
  loading: Object.freeze({
    kind: "loading",
    message: "Przygotowujemy poranną odprawę.",
  }),
  failure: Object.freeze({
    kind: "failure",
    header: previewHeader,
    message: "Nie udało się teraz odświeżyć briefingu.",
    supportingText: "Twoje dane są bezpieczne. Możesz spróbować ponownie za chwilę.",
    retryLabel: "Spróbuj ponownie",
  }),
});
