from datetime import datetime, timedelta
import inspect
from unittest.mock import Mock

import pytest
import application.morning_coach_use_case as morning_coach_use_case_module

from application import (
    AdaptationPolicy,
    AthleteAssessmentBuilder,
    AthleteKnowledgeContextBuilder,
    ExplainabilityResult,
    IntelligenceDecisionResult,
    MorningCoachPresenter,
    MorningCoachResult,
    MorningCoachUseCase,
    TrainingAssessmentBuilder,
)
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import (
    AthleteMemorySnapshot,
    DateRange,
    PatternReport,
    TrainingTrendReport,
)
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.trends import TrendEngine
from athlete.review.models import WeeklyTrainingReview
from athlete.review.weekly import WeeklyReviewService
from core.database import Database
from decision.models import DecisionResult, WorkoutPlan
from decision.sports import Sport
from engines.context_builder import ContextBuilder
from planner.models import PlannedWorkout
from recommendation import RecommendationResult
from schema.athlete_memory_schema import AthleteMemorySchema
from tests.helpers import (
    build_athlete,
    build_context,
    build_health,
    build_performance,
    build_recovery,
)
from workout.enums import WorkoutType


def build_review(context) -> WeeklyTrainingReview:
    as_of = datetime.combine(context.today.date, datetime.min.time())
    period = DateRange(
        start=as_of - timedelta(days=6),
        end=as_of + timedelta(days=1),
    )
    trends = TrainingTrendReport(
        period=period,
        workouts_count=1,
        planned_duration=60,
        executed_duration=60,
        planned_tss=50,
        executed_tss=50,
        average_completion_score=100.0,
        average_execution_score=100.0,
    )
    patterns = PatternReport(period=period, patterns=(), source_event_ids=())

    return WeeklyTrainingReview(
        period=period,
        trends=trends,
        patterns=patterns,
        source_event_ids=(),
    )


def build_plan() -> WorkoutPlan:
    decision = DecisionResult(
        sport=Sport.CYCLING,
        recommendation=WorkoutType.ENDURANCE,
        duration=60,
        target_tss=50,
        intensity="50 TSS/h",
        reasons=[],
    )
    plan = WorkoutPlan()
    plan.add_result(decision)

    return plan


def build_planned_workout() -> PlannedWorkout:
    return PlannedWorkout(
        name="Endurance",
        sport="cycling",
        target_tss=50,
        estimated_duration=60,
        blocks=[],
    )


def build_snapshot(context) -> AthleteMemorySnapshot:
    review = build_review(context)
    return AthleteMemorySnapshot(
        period=review.period,
        workout_observations=(),
        source_event_ids=(),
        schema_version=1,
    )


def build_use_case(
    *,
    weekly_review_workflow,
    context_builder=None,
    athlete=None,
):
    context = build_context()
    athlete = athlete or build_athlete(recovery_score=70, fatigue=79)
    plan = build_plan()
    planned_workout = build_planned_workout()
    intelligence = IntelligenceDecisionResult(
        observations=(),
        insights=(),
        plan=plan,
        decision=plan.decision,
        recommendations=RecommendationResult((), None),
        explainability=ExplainabilityResult(
            summary="Canonical summary.",
            contributing_factors=("Canonical factor.",),
            recommendations=("Canonical recommendation.",),
        ),
    )
    dependencies = {
        "health_repository": Mock(),
        "context_builder": context_builder if context_builder is not None else Mock(),
        "health_engine": Mock(),
        "recovery_engine": Mock(),
        "performance_engine": Mock(),
        "athlete_state_builder": Mock(),
        "weekly_review_workflow": weekly_review_workflow,
        "knowledge_context_builder": AthleteKnowledgeContextBuilder(),
        "training_assessment_builder": TrainingAssessmentBuilder(),
        "athlete_assessment_builder": AthleteAssessmentBuilder(),
        "adaptation_policy": AdaptationPolicy(),
        "intelligence_workflow": Mock(),
        "planner_engine": Mock(),
        "morning_coach_presenter": MorningCoachPresenter(),
    }
    dependencies["health_repository"].load_daily.return_value = [object()]
    if isinstance(dependencies["context_builder"], Mock):
        dependencies["context_builder"].build.return_value = context
    dependencies["health_engine"].analyze.return_value = build_health()
    dependencies["recovery_engine"].analyze.return_value = build_recovery(70)
    dependencies["performance_engine"].analyze.return_value = build_performance(79)
    dependencies["athlete_state_builder"].build.return_value = athlete
    dependencies["intelligence_workflow"].run.return_value = intelligence
    dependencies["planner_engine"].build.return_value = planned_workout

    return MorningCoachUseCase(**dependencies), dependencies, context, athlete, plan, planned_workout


def test_use_case_composes_happy_path_and_preserves_all_results():
    context = build_context()
    weekly_review_workflow = Mock()
    snapshot = build_snapshot(context)
    weekly_review_workflow.run_with_snapshot.return_value = (
        snapshot,
        build_review(context),
    )
    use_case, dependencies, _, athlete, plan, planned_workout = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )

    result = use_case.run()

    assert isinstance(result, MorningCoachResult)
    assert result.athlete_state is athlete
    assert (
        result.weekly_review
        is weekly_review_workflow.run_with_snapshot.return_value[1]
    )
    assert result.knowledge_context.athlete_state is athlete
    assert result.training_assessment.status.value == "no_clear_pattern"
    assert result.athlete_assessment.status.value == "stable"
    assert result.adaptation.status.value == "maintain"
    assert result.decision is plan
    assert result.planned_workout is planned_workout
    assert result.report.workout is planned_workout
    dependencies["intelligence_workflow"].run.assert_called_once()
    workflow_call = dependencies["intelligence_workflow"].run.call_args
    assert workflow_call.args == (athlete,)
    assert workflow_call.kwargs["snapshot"] is snapshot
    assert workflow_call.kwargs["adaptation"] is result.adaptation
    assert workflow_call.kwargs["health"].observed_at == datetime.combine(
        context.today.date,
        datetime.min.time(),
    )
    assert workflow_call.kwargs["health"].evidence == (
        f"health_daily:{context.today.date.isoformat()}",
    )
    assert result.report.explanation.summary == "Canonical summary."
    assert result.report.explanation.reasons == (
        "Canonical factor.",
        "Canonical recommendation.",
    )
    assert not hasattr(use_case, "decision_engine")
    dependencies["planner_engine"].build.assert_called_once_with(
        plan.decision,
        athlete,
    )


def test_use_case_uses_health_context_date_for_weekly_review_period():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, _, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )

    use_case.run()

    as_of = datetime.combine(context.today.date, datetime.min.time())
    weekly_review_workflow.run_with_snapshot.assert_called_once_with(
        DateRange(
            start=as_of - timedelta(days=6),
            end=as_of + timedelta(days=1),
        ),
    )


def test_use_case_reports_insufficient_data_for_empty_athlete_memory(tmp_path):
    database = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(database).create()
    workflow = WeeklyReviewWorkflow(
        AthleteMemoryReader(AthleteMemoryRepository(database)),
        TrendEngine(),
        PatternDetector(),
        WeeklyReviewService(),
    )
    use_case, _, _, _, _, _ = build_use_case(
        weekly_review_workflow=workflow,
    )

    result = use_case.run()

    assert result.weekly_review.trends.workouts_count == 0
    assert result.training_assessment.status.value == "no_training_data"
    assert result.athlete_assessment.status.value == "insufficient_data"
    assert result.adaptation.status.value == "insufficient_data"

    database.close()


def test_use_case_propagates_missing_health_data_without_running_memory_workflow():
    weekly_review_workflow = Mock()
    health_repository = Mock()
    health_repository.load_daily.return_value = []
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
        context_builder=ContextBuilder(),
    )
    use_case.health_repository = health_repository

    with pytest.raises(ValueError, match="History is empty"):
        use_case.run()

    weekly_review_workflow.run_with_snapshot.assert_not_called()
    dependencies["intelligence_workflow"].run.assert_not_called()


def test_use_case_has_no_write_dependency_or_write_side_effects():
    weekly_review_workflow = Mock()
    context = build_context()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )

    use_case.run()

    assert not hasattr(use_case, "writer")
    assert not hasattr(use_case, "repository")
    assert not hasattr(use_case, "database")
    for dependency in dependencies.values():
        if isinstance(dependency, Mock):
            assert all(call[0] != "write" for call in dependency.method_calls)


def test_use_case_passes_the_canonical_result_to_the_presenter():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )
    presenter = Mock()
    expected_report = Mock()
    presenter.present.return_value = expected_report
    use_case.morning_coach_presenter = presenter

    result = use_case.run()

    intelligence = dependencies["intelligence_workflow"].run.return_value
    presenter.present.assert_called_once()
    assert presenter.present.call_args.kwargs["intelligence"] is intelligence
    assert (
        presenter.present.call_args.kwargs["intelligence"].recommendations
        is intelligence.recommendations
    )
    assert result.report is expected_report


def test_use_case_contains_no_alternative_decision_or_recommendation_pipeline():
    source = inspect.getsource(morning_coach_use_case_module)

    assert "DecisionEngine" not in source
    assert "RecommendationEngine" not in source
    assert "DecisionExplainabilityBuilder" not in source
    assert "ExplanationBuilder" not in source


def test_public_application_exports_are_available():
    assert MorningCoachUseCase.__name__ == "MorningCoachUseCase"
    assert MorningCoachResult.__name__ == "MorningCoachResult"
