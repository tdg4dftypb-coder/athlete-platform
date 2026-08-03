from dataclasses import dataclass
from datetime import datetime, time

from application.adaptation import AdaptationDirective
from application.body_composition_input import BodyCompositionInputBuilder
from application.decision_explainability import ExplainabilityResult
from application.decision_explainability import DecisionExplainabilityBuilder
from application.nutrition_input import NutritionInputBuilder
from athlete.intelligence.insights import InsightBuilder
from athlete.intelligence.models import (
    AthleteInsight,
    AthleteObservation,
    HealthObservationInput,
)
from athlete.intelligence.observation_projector import ObservationProjector
from athlete.memory.models import AthleteMemorySnapshot
from athlete.models import AthleteState
from body_composition import BodyCompositionAssessment, BodyCompositionEngine
from core.models import HealthDaily
from decision.engine import DecisionEngine
from decision.models import DecisionResult, WorkoutPlan
from nutrition import NutritionAssessment, NutritionEngine
from recommendation import (
    RecommendationContext,
    RecommendationEngine,
    RecommendationResult,
)


def build_default_recommendation_engine() -> RecommendationEngine:
    from application.composition import build_recommendation_engine

    return build_recommendation_engine()


@dataclass(frozen=True)
class IntelligenceDecisionResult:
    observations: tuple[AthleteObservation, ...]
    insights: tuple[AthleteInsight, ...]
    plan: WorkoutPlan
    decision: DecisionResult
    recommendations: RecommendationResult
    explainability: ExplainabilityResult
    nutrition: NutritionAssessment | None = None
    body_composition: BodyCompositionAssessment | None = None


class IntelligenceDecisionWorkflow:
    """Orchestrates the deterministic intelligence-to-decision application flow."""

    def __init__(
        self,
        observation_projector: ObservationProjector | None = None,
        insight_builder: InsightBuilder | None = None,
        decision_engine: DecisionEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        explainability_builder: DecisionExplainabilityBuilder | None = None,
        nutrition_input_builder: NutritionInputBuilder | None = None,
        nutrition_engine: NutritionEngine | None = None,
        body_composition_input_builder: (
            BodyCompositionInputBuilder | None
        ) = None,
        body_composition_engine: BodyCompositionEngine | None = None,
    ) -> None:
        self.observation_projector = observation_projector or ObservationProjector()
        self.insight_builder = insight_builder or InsightBuilder()
        self.decision_engine = decision_engine or DecisionEngine()
        self.recommendation_engine = (
            recommendation_engine or build_default_recommendation_engine()
        )
        self.explainability_builder = (
            explainability_builder or DecisionExplainabilityBuilder()
        )
        self.nutrition_input_builder = (
            nutrition_input_builder or NutritionInputBuilder()
        )
        self.nutrition_engine = nutrition_engine or NutritionEngine()
        self.body_composition_input_builder = (
            body_composition_input_builder or BodyCompositionInputBuilder()
        )
        self.body_composition_engine = (
            body_composition_engine or BodyCompositionEngine()
        )

    def run(
        self,
        athlete: AthleteState,
        health: HealthObservationInput | None = None,
        snapshot: AthleteMemorySnapshot | None = None,
        adaptation: AdaptationDirective | None = None,
        nutrition_health_history: tuple[HealthDaily, ...] = (),
        body_composition_health_history: tuple[HealthDaily, ...] | None = None,
        workout_start: datetime | None = None,
    ) -> IntelligenceDecisionResult:
        observations = self.observation_projector.project(snapshot, health)
        insights = self.insight_builder.build(
            observations,
            snapshot.workout_observations if snapshot is not None else (),
        )
        plan = self.decision_engine.decide(
            athlete,
            adaptation,
            insights,
        )
        decision = plan.decision
        dated_inputs = (
            *((health.observed_at,) if health is not None else ()),
            *((adaptation.as_of,) if adaptation is not None else ()),
            *(observation.observed_at for observation in observations),
        )
        body_composition_history = (
            nutrition_health_history
            if body_composition_health_history is None
            else body_composition_health_history
        )
        history_timestamps = tuple(
            datetime.combine(
                item.date,
                time.min,
                tzinfo=None,
            )
            for item in (
                *nutrition_health_history,
                *body_composition_history,
            )
        )
        as_of = max(
            dated_inputs if dated_inputs else history_timestamps,
            default=None,
        )
        body_composition = None
        nutrition = None
        if as_of is not None:
            body_composition_input = self.body_composition_input_builder.build(
                health_history=body_composition_history,
                as_of=as_of,
            )
            body_composition = self.body_composition_engine.analyze(
                body_composition_input
            )
            nutrition_input = self.nutrition_input_builder.build(
                decision,
                valid_for_date=as_of.date(),
                as_of=as_of,
                health_history=nutrition_health_history,
                recovery_score=(
                    health.recovery_score if health is not None else None
                ),
                workout_start=workout_start,
                evidence=health.evidence if health is not None else (),
            )
            nutrition = self.nutrition_engine.analyze(nutrition_input)
        recommendations = self.recommendation_engine.evaluate(
            RecommendationContext(
                decision=decision,
                insights=insights,
                observations=observations,
                as_of=as_of,
                nutrition_assessment=nutrition,
            )
        )
        explainability = self.explainability_builder.build(
            decision.decision_reasons,
            recommendations,
        )

        return IntelligenceDecisionResult(
            observations=observations,
            insights=insights,
            plan=plan,
            decision=decision,
            recommendations=recommendations,
            explainability=explainability,
            nutrition=nutrition,
            body_composition=body_composition,
        )
