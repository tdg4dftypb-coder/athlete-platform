import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type { AthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-v1";
import { mapActivityToIcon } from "../components/icon";
import type {
  TechnicalDetailsPresentation,
  TrainingHeroPresentation,
  TrainingPresentation,
  TrainingPresentationHeader,
  WorkoutBlockPresentation,
} from "../models/training-presentation";
import type { TrainingPresentationState } from "../models/training-presentation-state";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";
import type { MappingContext } from "./mapping-context";

export type PayloadMappedTrainingState = Exclude<
  TrainingPresentationState,
  { kind: "loading" }
>;

export function parseAndMapAthleteDashboardToTraining(
  input: unknown,
  context: MappingContext,
): PayloadMappedTrainingState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) {
    return failureState(
      `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
      context,
    );
  }
  return mapAthleteDashboardToTraining(parsed.data, context);
}

export function mapAthleteDashboardToTraining(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedTrainingState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return failureState("Payload zawiera niespójny kontekst czasu.", context);
  }

  const stale =
    payload.valid_for_date !== dateInTimeZone(context.now, context.timeZone) ||
    ageMs > context.staleAfterMs;
  const header = createHeader(payload, context, stale);

  if (payload.training.metadata.status === "unavailable") {
    return {
      kind: "unavailable",
      header,
      message: "Plan treningowy nie jest dzisiaj dostępny.",
      reason: "Brak przypisanego treningu w dzisiejszej decyzji planisty.",
      nextAction: "Sprawdź ponownie po kolejnej synchronizacji danych.",
    };
  }

  const missingData = collectMissingData(payload);
  const training = createTraining(payload, header);

  if (stale) {
    return {
      kind: "stale",
      training,
      message: "Ten plan treningowy może nie odzwierciedlać dzisiejszego stanu.",
      lastUpdatedText: header.lastUpdatedText,
    };
  }

  if (missingData.length > 0) {
    return {
      kind: "partial",
      training,
      message: "Plan treningowy jest dostępny, ale brakuje części parametrów.",
      missingData,
    };
  }

  return { kind: "ready", training };
}

function createHeader(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
  stale: boolean,
): TrainingPresentationHeader {
  const date = parseContractDate(payload.valid_for_date);
  const asOf = parseContractTimestamp(payload.as_of);
  return {
    title: "Trening",
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

function createTraining(
  payload: AthleteDashboardPayloadV1,
  header: TrainingPresentationHeader,
): TrainingPresentation {
  const workoutName = payload.training.workout_name ?? "Trening dzisiejszy";
  const durationMin = payload.training.estimated_duration_minutes;
  const goal = payload.training.workout_goal;

  const hero: TrainingHeroPresentation = {
    activityIcon: mapActivityToIcon(workoutName),
    title: workoutName,
    description: formatDescription(workoutName, goal),
    durationText: durationMin !== null ? `${durationMin} min` : "Czas nieokreślony",
    intensityText: formatIntensityLabel(goal),
    targetGoalText: formatTargetGoal(goal),
  };

  const objective = formatObjective(goal);
  const structure = createWorkoutStructure(payload);
  const notes = createTrainingNotes(goal);
  const expectedOutcome = formatExpectedOutcome(goal);
  const technicalDetails = createTechnicalDetails(payload);

  return {
    source: "payload",
    header,
    hero,
    objective,
    structure,
    notes,
    expectedOutcome,
    technicalDetails,
  };
}

function formatDescription(
  workoutName: string,
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): string {
  if (goal === "THRESHOLD") {
    return "Jazda z akcentem na pracę w strefie progu beztlenowego dla podniesienia wydolności.";
  }
  if (goal === "VO2") {
    return "Trening wysokiej intensywności z naciskiem na maksymalny pobór tlenu.";
  }
  if (goal === "ENDURANCE") {
    return "Tlenowa jazda wytrzymałościowa dla budowania ogólnej bazy i spalania tłuszczu.";
  }
  if (goal === "TEMPO") {
    return "Jazda w strefie tempa (Strefa 3) dla zwiększenia pojemności glikogenowej.";
  }
  if (goal === "RECOVERY") {
    return "Aktywna regeneracja przy niskiej intensywności przyspieszająca odbudowę tkankową.";
  }
  return `Plan treningowy: ${workoutName}`;
}

function formatIntensityLabel(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): string {
  switch (goal) {
    case "THRESHOLD":
      return "Próg (Strefa 4)";
    case "VO2":
      return "VO₂max (Strefa 5)";
    case "TEMPO":
      return "Tempo (Strefa 3)";
    case "ENDURANCE":
      return "Wytrzymałość (Strefa 2)";
    case "RECOVERY":
      return "Regeneracja (Strefa 1)";
    default:
      return "Umiarkowany";
  }
}

function formatTargetGoal(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): string {
  switch (goal) {
    case "THRESHOLD":
      return "Zwiększenie mocy na progu FTP";
    case "VO2":
      return "Rozbudowa maksymalnej pojemności tlenowej";
    case "TEMPO":
      return "Zwiększenie tolerancji wysiłku w Strefie 3";
    case "ENDURANCE":
      return "Budowanie ogólnej bazy tlenowej";
    case "RECOVERY":
      return "Przyspieszenie regeneracji mięśniowej";
    default:
      return "Adaptacja treningowa";
  }
}

function formatObjective(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): string {
  switch (goal) {
    case "THRESHOLD":
      return "Dzisiaj budujemy wytrzymałość progową i sprawność krążeniowo-oddechową przy stabilnej kadencji.";
    case "VO2":
      return "Dzisiaj budujemy szczytowy pobór tlenu (VO₂max) i dynamikę reakcji sercowo-naczyniowej.";
    case "TEMPO":
      return "Dzisiaj budujemy wytrzymałość tempową i stabilność mocy w Strefie 3.";
    case "ENDURANCE":
      return "Dzisiaj budujemy ogólną wydolność tlenową i odporność na zmęczenie przy niskim koszcie energetycznym.";
    case "RECOVERY":
      return "Dzisiaj budujemy aktywną regenerację i podtrzymujemy krążenie bez obciążania układu nerwowego.";
    default:
      return "Dzisiaj realizujemy cel treningowy dostosowany do Twojego bieżącego stanu regeneracji.";
  }
}

function createWorkoutStructure(
  payload: AthleteDashboardPayloadV1,
): readonly WorkoutBlockPresentation[] {
  const duration = payload.training.estimated_duration_minutes;
  const goal = payload.training.workout_goal;

  if (duration === null || duration <= 0) {
    return [
      {
        id: "main-block",
        name: "Główny blok treningowy",
        durationText: "Czas nieokreślony",
        intensityText: formatIntensityLabel(goal),
        description: "Wykonaj trening zgodnie z wytycznymi trenera.",
      },
    ];
  }

  const warmupMin = Math.min(10, Math.floor(duration * 0.2));
  const cooldownMin = Math.min(8, Math.floor(duration * 0.15));
  const mainMin = Math.max(5, duration - warmupMin - cooldownMin);

  return [
    {
      id: "warmup",
      name: "Rozgrzewka",
      durationText: `${warmupMin} min`,
      intensityText: "Strefa 1–2",
      description: "Swobodne kręcenie, stopniowe podnoszenie tętna i kadencji.",
    },
    {
      id: "main-work",
      name: `Część główna (${formatIntensityLabel(goal)})`,
      durationText: `${mainMin} min`,
      intensityText: formatIntensityLabel(goal),
      description: formatMainWorkDescription(goal, mainMin),
    },
    {
      id: "cooldown",
      name: "Schłodzenie",
      durationText: `${cooldownMin} min`,
      intensityText: "Strefa 1",
      description: "Spokojne wyciszenie organizmu, wyrównanie oddechu.",
    },
  ];
}

function formatMainWorkDescription(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
  mainMinutes: number,
): string {
  if (goal === "THRESHOLD") {
    const reps = Math.max(2, Math.floor(mainMinutes / 10));
    const repLen = Math.floor(mainMinutes / reps);
    return `${reps} powtórzenia po ${repLen} minut na progu FTP z przerwą w Strefie 1.`;
  }
  if (goal === "VO2") {
    return "Seria krótkich, intensywnych powtórzeń w Strefie 5 z pełnym odpoczynkiem.";
  }
  return `Ciągły wysiłek w akcentowanej strefie przez około ${mainMinutes} minut.`;
}

function createTrainingNotes(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): readonly string[] {
  const notes: string[] = [
    "Pij regularnie w trakcie wysiłku.",
    "Utrzymuj stabilną pozycję na siodełku.",
  ];

  if (goal === "THRESHOLD" || goal === "VO2") {
    notes.unshift("Utrzymuj płynną kadencję 90–95 RPM w trakcie powtórzeń.");
    notes.push("Nie zaczynaj pierwszego powtórzenia powyżej zakładanej mocy.");
  } else {
    notes.unshift("Jazda w tlenowej strefie bez gwałtownych przyśpieszeń.");
  }

  return notes;
}

function formatExpectedOutcome(
  goal: AthleteDashboardPayloadV1["training"]["workout_goal"],
): string {
  if (goal === "THRESHOLD") {
    return "Po treningu powinieneś czuć umiarkowane zmęczenie nóg, ale bez uczucia głębokiego wyczerpania. Trening stymuluje adaptacje krążeniowo-oddechowe.";
  }
  if (goal === "VO2") {
    return "Po treningu odczujesz mocne zmęczenie obwodowe i oddechowe. Zdbaj o natychmiastowe uzupełnienie węglowodanów.";
  }
  if (goal === "RECOVERY") {
    return "Po treningu powinieneś czuć się odświeżony i rozgrzany. Wysiłek nie powoduje akumulacji zmęczenia.";
  }
  return "Trening wywołuje planowaną odpowiedź adaptacyjną bez nadmiernego przeciążenia organizmu.";
}

function createTechnicalDetails(
  payload: AthleteDashboardPayloadV1,
): TechnicalDetailsPresentation | null {
  const targetIf = payload.training.target_if;
  const targetTss = payload.training.target_tss;
  const duration = payload.training.estimated_duration_minutes;
  const energy = payload.health.active_energy_kcal;

  if (
    targetIf === null &&
    targetTss === null &&
    duration === null &&
    energy === null
  ) {
    return null;
  }

  return {
    intensityFactor: targetIf !== null ? `${targetIf} IF` : null,
    tss: targetTss !== null ? `${targetTss} TSS` : null,
    np: null, // Payload v1.0 does not supply NP directly
    duration: duration !== null ? `${duration} min` : null,
    estimatedEnergy: energy !== null ? `${energy} kcal` : null,
  };
}

function collectMissingData(
  payload: AthleteDashboardPayloadV1,
): readonly string[] {
  const missing: string[] = [];
  if (payload.training.workout_name === null) missing.push("Brak nazwy treningu");
  if (payload.training.estimated_duration_minutes === null) missing.push("Brak przewidywanego czasu");
  if (payload.training.metadata.status === "partial") missing.push("Sekcja treningowa ma niepełne dane");
  return missing;
}


function failureState(
  supportingText: string,
  context: MappingContext,
): PayloadMappedTrainingState {
  return {
    kind: "failure",
    header: {
      title: "Trening",
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long",
        day: "numeric",
        month: "long",
        timeZone: context.timeZone,
      }).format(context.now),
      lastUpdatedText: "Aktualizacja niedostępna",
      freshnessLabel: null,
    },
    message: "Nie udało się teraz przygotować widoku treningu.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}
