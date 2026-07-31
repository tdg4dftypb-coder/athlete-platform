from collections.abc import Callable

from application.adaptation import AdaptationPolicy
from application.athlete_assessment import AthleteAssessmentBuilder
from application.decision_explainability import DecisionExplainabilityBuilder
from application.intelligence_decision_workflow import IntelligenceDecisionWorkflow
from application.knowledge_context import AthleteKnowledgeContextBuilder
from application.morning_coach import MorningCoachPresenter
from application.morning_coach_use_case import (
    HealthHistoryReader,
    MorningCoachUseCase,
)
from application.training_assessment import TrainingAssessmentBuilder
from application.weekly_review import WeeklyReviewWorkflow
from athlete.intelligence.insights import InsightBuilder
from athlete.intelligence.observation_projector import ObservationProjector
from athlete.memory import (
    AthleteMemoryReader,
    AthleteMemoryRepository,
    PatternDetector,
    TrendEngine,
)
from athlete.review import WeeklyReviewService
from athlete.state_builder import AthleteStateBuilder
from core.database import Database
from core.models import HealthDaily
from decision.engine import DecisionEngine
from engines.context_builder import ContextBuilder
from health.engine import HealthEngine
from performance.engine import PerformanceEngine
from planner.engine import PlannerEngine
from recommendation import (
    HydrationRecommendationRule,
    MobilityRecommendationRule,
    RecommendationBuilder,
    RecommendationEngine,
    RecoveryRecommendationRule,
    SleepRecommendationRule,
)
from recovery.engine import RecoveryEngine
from repositories.health_repository import HealthRepository


class _DeferredHealthHistoryReader:
    def __init__(
        self,
        factory: Callable[[], HealthHistoryReader],
    ) -> None:
        self._factory = factory
        self._reader: HealthHistoryReader | None = None

    def load_daily(self) -> list[HealthDaily]:
        if self._reader is None:
            self._reader = self._factory()
        return self._reader.load_daily()


def build_decision_engine() -> DecisionEngine:
    return DecisionEngine()


def build_planner_engine() -> PlannerEngine:
    return PlannerEngine()


def build_recommendation_engine() -> RecommendationEngine:
    return RecommendationEngine(
        rules=(
            SleepRecommendationRule(),
            HydrationRecommendationRule(),
            RecoveryRecommendationRule(),
            MobilityRecommendationRule(),
        ),
        builder=RecommendationBuilder(),
    )


def build_intelligence_decision_workflow() -> IntelligenceDecisionWorkflow:
    return IntelligenceDecisionWorkflow(
        observation_projector=ObservationProjector(),
        insight_builder=InsightBuilder(),
        decision_engine=build_decision_engine(),
        recommendation_engine=build_recommendation_engine(),
        explainability_builder=DecisionExplainabilityBuilder(),
    )


def build_weekly_review_workflow(database: Database) -> WeeklyReviewWorkflow:
    return WeeklyReviewWorkflow(
        reader=AthleteMemoryReader(AthleteMemoryRepository(database)),
        trend_engine=TrendEngine(),
        pattern_detector=PatternDetector(),
        review_service=WeeklyReviewService(),
    )


def build_morning_coach_use_case(
    database: Database,
    health_repository: HealthHistoryReader | None = None,
) -> MorningCoachUseCase:
    return MorningCoachUseCase(
        health_repository=(
            health_repository
            if health_repository is not None
            else _DeferredHealthHistoryReader(HealthRepository)
        ),
        context_builder=ContextBuilder(),
        health_engine=HealthEngine(),
        recovery_engine=RecoveryEngine(),
        performance_engine=PerformanceEngine(),
        athlete_state_builder=AthleteStateBuilder(),
        weekly_review_workflow=build_weekly_review_workflow(database),
        knowledge_context_builder=AthleteKnowledgeContextBuilder(),
        training_assessment_builder=TrainingAssessmentBuilder(),
        athlete_assessment_builder=AthleteAssessmentBuilder(),
        adaptation_policy=AdaptationPolicy(),
        intelligence_workflow=build_intelligence_decision_workflow(),
        planner_engine=build_planner_engine(),
        morning_coach_presenter=MorningCoachPresenter(),
    )
