from dataclasses import dataclass

from application.adaptation import AdaptationDirective
from application.decision_explainability import ExplainabilityResult
from application.decision_explainability import DecisionExplainabilityBuilder
from athlete.intelligence.insights import InsightBuilder
from athlete.intelligence.models import (
    AthleteInsight,
    AthleteObservation,
    HealthObservationInput,
)
from athlete.intelligence.observation_projector import ObservationProjector
from athlete.memory.models import AthleteMemorySnapshot
from athlete.models import AthleteState
from decision.engine import DecisionEngine
from decision.models import DecisionResult, WorkoutPlan
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


class IntelligenceDecisionWorkflow:
    """Orchestrates the deterministic intelligence-to-decision application flow."""

    def __init__(
        self,
        observation_projector: ObservationProjector | None = None,
        insight_builder: InsightBuilder | None = None,
        decision_engine: DecisionEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        explainability_builder: DecisionExplainabilityBuilder | None = None,
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

    def run(
        self,
        athlete: AthleteState,
        health: HealthObservationInput | None = None,
        snapshot: AthleteMemorySnapshot | None = None,
        adaptation: AdaptationDirective | None = None,
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
        recommendations = self.recommendation_engine.evaluate(
            RecommendationContext(
                decision=decision,
                insights=insights,
                observations=observations,
                as_of=max(
                    (
                        *((health.observed_at,) if health is not None else ()),
                        *((adaptation.as_of,) if adaptation is not None else ()),
                        *(
                            observation.observed_at
                            for observation in observations
                        ),
                    ),
                    default=None,
                ),
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
        )
