import { parseAthleteDashboardPayloadV1 } from "../contracts/athlete-dashboard-payload-parser";
import type {
  AthleteDashboardPayloadV1,
  DashboardDecisionReason,
  DashboardGoalType,
  DashboardTrainingObjective,
} from "../contracts/athlete-dashboard-payload-v1";
import type { MorningBriefingPresentation } from "../models/morning-briefing-presentation";
import type { MorningBriefingPresentationState } from "../models/morning-briefing-presentation-state";
import type { MappingContext } from "./mapping-context";
import {
  dateInTimeZone,
  formatContractDateTime,
  parseContractDate,
  parseContractTimestamp,
} from "./contract-temporal";

export type PayloadMappedPresentationState = Exclude<MorningBriefingPresentationState, { kind: "loading" }>;

export function parseAndMapAthleteDashboardToMorningBriefing(
  input: unknown,
  context: MappingContext,
): PayloadMappedPresentationState {
  const parsed = parseAthleteDashboardPayloadV1(input);
  if (!parsed.success) return failureState(
    `Payload nie przeszedł walidacji: ${parsed.issues[0]?.path ?? "dashboard"}.`,
    context,
  );
  return mapAthleteDashboardToMorningBriefing(parsed.data, context);
}

export function mapAthleteDashboardToMorningBriefing(
  payload: AthleteDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedPresentationState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return failureState("Payload zawiera niespójny kontekst czasu.", context);
  }
  const header = createHeader(payload, context);
  if (!hasKeyDecision(payload)) {
    return {
      kind: "unavailable",
      header,
      message: "Nie mamy dziś wystarczających danych, aby przygotować wiarygodny briefing.",
      reason: firstLimitation(payload.training.metadata.limitations, "Brakuje aktualnej decyzji treningowej."),
      nextAction: "Sprawdź ponownie po kolejnej synchronizacji danych.",
    };
  }

  const briefing = createBriefing(payload, context);
  const stale = payload.valid_for_date !== dateInTimeZone(context.now, context.timeZone) || ageMs > context.staleAfterMs;
  if (stale) {
    return {
      kind: "stale",
      briefing,
      message: "To podsumowanie opiera się na nieaktualnych danych.",
      lastUpdatedText: `Ostatnia aktualizacja: ${formatContractDateTime(asOf, context)}.`,
    };
  }

  const missingData = supportingDataGaps(payload);
  if (missingData.length > 0) {
    return {
      kind: "partial",
      briefing,
      message: "Dzisiejszy plan jest dostępny, ale ocena opiera się na niepełnych danych.",
      missingData,
    };
  }

  return { kind: "ready", briefing };
}

function createHeader(payload: AthleteDashboardPayloadV1, context: MappingContext) {
  const date = parseContractDate(payload.valid_for_date);
  return {
    greeting: "Dzień dobry",
    athleteName: context.athleteName,
    dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
      weekday: "long", day: "numeric", month: "long", timeZone: context.timeZone,
    }).format(date),
    timeText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
      hour: "2-digit", minute: "2-digit", timeZone: context.timeZone,
    }).format(parseContractTimestamp(payload.as_of)),
  };
}

function createBriefing(payload: AthleteDashboardPayloadV1, context: MappingContext): MorningBriefingPresentation {
  const header = createHeader(payload, context);
  const decisionTitle = payload.training.workout_name!;
  const recommendationMessages = payload.recommendations.items.map((item) => item.message);
  const reasons = payload.training.decision_reasons.map(decisionReasonLabel);
  const plan = [decisionTitle];
  if (payload.nutrition.fueling_pre_workout_carbohydrate_g !== null) {
    plan.push(`${formatNumber(payload.nutrition.fueling_pre_workout_carbohydrate_g, context)} g węglowodanów przed treningiem`);
  }
  const primaryRecommendation = recommendationMessages[0];
  if (primaryRecommendation) plan.push(primaryRecommendation);

  return {
    ...header,
    coachMessage: [
      `Dzisiejsza decyzja to ${decisionTitle.toLocaleLowerCase(context.locale ?? "pl-PL")}.`,
      ...recommendationMessages,
    ],
    decision: {
      title: decisionTitle,
      duration: `${payload.training.estimated_duration_minutes} minut`,
      intensity: trainingObjectiveLabel(payload.training.workout_goal!),
    },
    reasons,
    changesSinceYesterday: [],
    todayPlan: plan,
    goal: {
      title: goalLabel(payload.goal.goal_type, payload.goal.target_body_mass_kg, context),
      progressAccessibilityLabel: "Postęp celu",
      progressLabel: "Postęp niedostępny",
      progressValue: null,
      timeline: goalTimeline(payload.goal.valid_from, payload.goal.valid_until, context),
    },
    shortcuts: [
      { id: "recovery", label: "Regeneracja" },
      { id: "training", label: "Trening" },
      { id: "nutrition", label: "Odżywianie" },
      { id: "history", label: "Historia" },
    ],
  };
}

function hasKeyDecision(payload: AthleteDashboardPayloadV1): boolean {
  return payload.training.metadata.status !== "unavailable"
    && payload.recommendations.metadata.status !== "unavailable"
    && payload.training.workout_name !== null
    && payload.training.workout_goal !== null
    && payload.training.estimated_duration_minutes !== null
    && payload.training.decision_action !== null;
}

function supportingDataGaps(payload: AthleteDashboardPayloadV1): readonly string[] {
  const gaps = new Set<string>();
  if (payload.health.hrv_ms === null) gaps.add("Brak HRV");
  if (payload.health.sleep_minutes === null) gaps.add("Brak danych snu");
  if (payload.health.metadata.status !== "ready") gaps.add("Niepełne dane zdrowotne");
  if (payload.recovery.metadata.status !== "ready") gaps.add("Brak pełnej oceny regeneracji");
  if (payload.performance.metadata.status !== "ready") gaps.add("Niepełne dane obciążenia");
  if (payload.nutrition.metadata.status !== "ready") gaps.add("Niepełne dane odżywiania");
  if (payload.goal.metadata.status !== "ready") gaps.add("Niepełne dane celu");
  if (payload.recommendations.metadata.status !== "ready") gaps.add("Niepełne dane rekomendacji");
  if (payload.data_quality.metadata.status !== "ready") gaps.add("Ogólna jakość danych jest niepełna");
  return [...gaps];
}

function failureState(supportingText: string, context: MappingContext): PayloadMappedPresentationState {
  return {
    kind: "failure",
    header: {
      greeting: "Dzień dobry",
      athleteName: context.athleteName,
      dateText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        weekday: "long", day: "numeric", month: "long", timeZone: context.timeZone,
      }).format(context.now),
      timeText: new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
        hour: "2-digit", minute: "2-digit", timeZone: context.timeZone,
      }).format(context.now),
    },
    message: "Nie udało się teraz przygotować briefingu.",
    supportingText,
    retryLabel: "Spróbuj ponownie",
  };
}

function formatNumber(value: number, context: MappingContext): string {
  return new Intl.NumberFormat(context.locale ?? "pl-PL", { maximumFractionDigits: 0 }).format(value);
}

function goalLabel(goalType: DashboardGoalType | null, target: number | null, context: MappingContext): string {
  if (goalType === "reduce_body_mass" && target !== null) return `Masa docelowa ${formatNumber(target, context)} kg`;
  if (goalType === "maintain") return "Utrzymanie masy ciała";
  return "Cel niedostępny";
}

function goalTimeline(from: string | null, until: string | null, context: MappingContext): string {
  if (!from && !until) return "Brak zakresu celu";
  const format = (value: string) => new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
    day: "numeric", month: "short", year: "numeric", timeZone: context.timeZone,
  }).format(parseContractDate(value));
  if (from && until) return `${format(from)} – ${format(until)}`;
  return from ? `Od ${format(from)}` : `Do ${format(until!)}`;
}

function firstLimitation(limitations: readonly string[], fallback: string): string {
  return limitations[0] ?? fallback;
}

function trainingObjectiveLabel(value: DashboardTrainingObjective): string {
  const labels: Record<DashboardTrainingObjective, string> = {
    REST: "Odpoczynek", RECOVERY: "Regeneracja", ENDURANCE: "Wytrzymałość", TEMPO: "Tempo",
    SWEET_SPOT: "Sweet spot", THRESHOLD: "Próg", VO2: "VO₂ max", ANAEROBIC: "Beztlenowo", SPRINT: "Sprint",
  };
  return labels[value];
}

function decisionReasonLabel(value: DashboardDecisionReason): string {
  const labels: Record<DashboardDecisionReason, string> = {
    adaptation_reduce_load: "Obciążenie zostało ograniczone",
    insight_need_more_recovery: "Organizm potrzebuje więcej regeneracji",
    insight_fatigue_accumulating: "Zmęczenie narasta",
    insight_high_training_compliance: "Plan treningowy jest realizowany regularnie",
  };
  return labels[value];
}
