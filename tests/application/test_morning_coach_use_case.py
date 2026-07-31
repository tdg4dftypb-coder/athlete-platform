from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from application import (
    AdaptationPolicy,
    AthleteAssessmentBuilder,
    AthleteKnowledgeContextBuilder,
    MorningCoachBuilder,
    MorningCoachResult,
    MorningCoachUseCase,
    TrainingAssessmentBuilder,
)
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import DateRange, PatternReport, TrainingTrendReport
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
        "decision_engine": Mock(),
        "planner_engine": Mock(),
        "morning_coach_builder": MorningCoachBuilder(),
    }
    dependencies["health_repository"].load_daily.return_value = [object()]
    if isinstance(dependencies["context_builder"], Mock):
        dependencies["context_builder"].build.return_value = context
    dependencies["health_engine"].analyze.return_value = build_health()
    dependencies["recovery_engine"].analyze.return_value = build_recovery(70)
    dependencies["performance_engine"].analyze.return_value = build_performance(79)
    dependencies["athlete_state_builder"].build.return_value = athlete
    dependencies["decision_engine"].decide.return_value = plan
    dependencies["planner_engine"].build.return_value = planned_workout

    return MorningCoachUseCase(**dependencies), dependencies, context, athlete, plan, planned_workout


def test_use_case_composes_happy_path_and_preserves_all_results():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run.return_value = build_review(context)
    use_case, dependencies, _, athlete, plan, planned_workout = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )

    result = use_case.run()

    assert isinstance(result, MorningCoachResult)
    assert result.athlete_state is athlete
    assert result.weekly_review is weekly_review_workflow.run.return_value
    assert result.knowledge_context.athlete_state is athlete
    assert result.training_assessment.status.value == "no_clear_pattern"
    assert result.athlete_assessment.status.value == "stable"
    assert result.adaptation.status.value == "maintain"
    assert result.decision is plan
    assert result.planned_workout is planned_workout
    assert result.report.workout is planned_workout
    dependencies["decision_engine"].decide.assert_called_once_with(
        athlete,
        result.adaptation,
    )
    dependencies["planner_engine"].build.assert_called_once_with(
        plan.decision,
        athlete,
    )


def test_use_case_uses_health_context_date_for_weekly_review_period():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run.return_value = build_review(context)
    use_case, _, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
    )

    use_case.run()

    as_of = datetime.combine(context.today.date, datetime.min.time())
    weekly_review_workflow.run.assert_called_once_with(
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

    weekly_review_workflow.run.assert_not_called()
    dependencies["decision_engine"].decide.assert_not_called()


def test_use_case_has_no_write_dependency_or_write_side_effects():
    weekly_review_workflow = Mock()
    weekly_review_workflow.run.return_value = build_review(build_context())
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


def test_public_application_exports_are_available():
    assert MorningCoachUseCase.__name__ == "MorningCoachUseCase"
    assert MorningCoachResult.__name__ == "MorningCoachResult"
