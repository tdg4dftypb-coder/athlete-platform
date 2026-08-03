from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Protocol

from application.adaptation import AdaptationDirective, AdaptationPolicy
from application.athlete_assessment import (
    AthleteAssessment,
    AthleteAssessmentBuilder,
)
from application.knowledge_context import (
    AthleteKnowledgeContext,
    AthleteKnowledgeContextBuilder,
)
from application.intelligence_decision_workflow import IntelligenceDecisionWorkflow
from application.morning_coach import MorningCoachPresenter, MorningCoachReport
from application.training_assessment import (
    TrainingAssessment,
    TrainingAssessmentBuilder,
)
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import DateRange
from athlete.intelligence.models import HealthObservationInput
from athlete.models import AthleteState
from athlete.review.models import WeeklyTrainingReview
from athlete.state_builder import AthleteStateBuilder
from core.models import HealthDaily
from decision.models import WorkoutPlan
from engines.context_builder import ContextBuilder
from health.engine import HealthEngine
from planner.engine import PlannerEngine
from planner.models import PlannedWorkout
from performance.engine import PerformanceEngine
from recovery.engine import RecoveryEngine


class HealthHistoryReader(Protocol):
    """Read the daily health history required by the morning workflow."""

    def load_daily(self) -> list[HealthDaily]: ...


@dataclass(frozen=True)
class MorningCoachResult:
    athlete_state: AthleteState
    weekly_review: WeeklyTrainingReview
    knowledge_context: AthleteKnowledgeContext
    training_assessment: TrainingAssessment
    athlete_assessment: AthleteAssessment
    adaptation: AdaptationDirective
    decision: WorkoutPlan
    planned_workout: PlannedWorkout
    report: MorningCoachReport


class MorningCoachUseCase:
    """Composes the deterministic daily coaching workflow from supplied services."""

    def __init__(
        self,
        health_repository: HealthHistoryReader,
        context_builder: ContextBuilder,
        health_engine: HealthEngine,
        recovery_engine: RecoveryEngine,
        performance_engine: PerformanceEngine,
        athlete_state_builder: AthleteStateBuilder,
        weekly_review_workflow: WeeklyReviewWorkflow,
        knowledge_context_builder: AthleteKnowledgeContextBuilder,
        training_assessment_builder: TrainingAssessmentBuilder,
        athlete_assessment_builder: AthleteAssessmentBuilder,
        adaptation_policy: AdaptationPolicy,
        intelligence_workflow: IntelligenceDecisionWorkflow,
        planner_engine: PlannerEngine,
        morning_coach_presenter: MorningCoachPresenter,
    ) -> None:
        self.health_repository = health_repository
        self.context_builder = context_builder
        self.health_engine = health_engine
        self.recovery_engine = recovery_engine
        self.performance_engine = performance_engine
        self.athlete_state_builder = athlete_state_builder
        self.weekly_review_workflow = weekly_review_workflow
        self.knowledge_context_builder = knowledge_context_builder
        self.training_assessment_builder = training_assessment_builder
        self.athlete_assessment_builder = athlete_assessment_builder
        self.adaptation_policy = adaptation_policy
        self.intelligence_workflow = intelligence_workflow
        self.planner_engine = planner_engine
        self.morning_coach_presenter = morning_coach_presenter

    def run(self) -> MorningCoachResult:
        health_history = self.health_repository.load_daily()
        health_history_snapshot = tuple(health_history)
        health_context = self.context_builder.build(
            health_history,
        )
        health = self.health_engine.analyze(health_context)
        recovery = self.recovery_engine.analyze(health_context)
        performance = self.performance_engine.analyze()
        athlete = self.athlete_state_builder.build(
            health=health,
            context=health_context,
            recovery=recovery,
            performance=performance,
        )

        as_of = datetime.combine(health_context.today.date, time.min)
        snapshot, weekly_review = self.weekly_review_workflow.run_with_snapshot(
            DateRange(
                start=as_of - timedelta(days=6),
                end=as_of + timedelta(days=1),
            ),
        )
        knowledge_context = self.knowledge_context_builder.build(
            as_of=as_of,
            athlete_state=athlete,
            weekly_review=weekly_review,
        )
        training_assessment = self.training_assessment_builder.build(
            knowledge_context,
        )
        athlete_assessment = self.athlete_assessment_builder.build(
            knowledge_context,
            training_assessment,
        )
        adaptation = self.adaptation_policy.evaluate(athlete_assessment)
        intelligence = self.intelligence_workflow.run(
            athlete,
            health=HealthObservationInput(
                observed_at=as_of,
                hrv_delta_percent=health_context.hrv.delta_percent,
                sleep_duration_minutes=health_context.today.sleep_duration,
                sleep_baseline_minutes=health_context.sleep.average_7,
                recovery_score=recovery.score,
                evidence=(f"health_daily:{health_context.today.date.isoformat()}",),
            ),
            snapshot=snapshot,
            adaptation=adaptation,
            nutrition_health_history=health_history_snapshot,
            body_composition_health_history=health_history_snapshot,
        )
        planned_workout = self.planner_engine.build(
            intelligence.decision,
            athlete,
        )
        report = self.morning_coach_presenter.present(
            intelligence=intelligence,
            planned_workout=planned_workout,
            athlete_state=athlete,
            athlete_assessment=athlete_assessment,
            weekly_review=weekly_review,
            adaptation=adaptation,
        )

        return MorningCoachResult(
            athlete_state=athlete,
            weekly_review=weekly_review,
            knowledge_context=knowledge_context,
            training_assessment=training_assessment,
            athlete_assessment=athlete_assessment,
            adaptation=adaptation,
            decision=intelligence.plan,
            planned_workout=planned_workout,
            report=report,
        )
