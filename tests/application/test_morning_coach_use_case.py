from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
import inspect
from unittest.mock import Mock

import pytest
import application.morning_coach_use_case as morning_coach_use_case_module

from adaptive import (
    BodyMassTrendQuality,
    BodyMassTrendQualityDataStatus,
    GoalAssessment,
    GoalAssessmentDataStatus,
)
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
    build_intelligence_decision_workflow,
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
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionProfile,
)
from core.database import Database
from core.models import HealthDaily
from decision.models import DecisionResult, WorkoutPlan
from decision.sports import Sport
from engines.context_builder import ContextBuilder
from planner.models import PlannedWorkout
from planner.engine import PlannerEngine
from recommendation import RecommendationResult, RecommendationType
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


def build_body_composition_assessment(
    as_of: datetime,
) -> BodyCompositionAssessment:
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=BodyCompositionDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        evidence=(),
        limitations=(
            "missing_body_mass",
            "missing_body_fat_percentage",
            "missing_muscle_mass",
            "missing_body_water_percentage",
            "missing_visceral_fat",
            "missing_basal_metabolic_rate",
            "missing_waist_circumference",
            "insufficient_body_mass_history",
        ),
        valid_for_date=as_of.date(),
        as_of=as_of,
    )


def build_body_mass_trend_quality(as_of: datetime) -> BodyMassTrendQuality:
    return BodyMassTrendQuality(
        measurement_count=0,
        period_days=None,
        current_is_fresh=False,
        baseline_window_valid=False,
        source_consistency_known=False,
        data_status=BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        evidence=(),
        limitations=("missing_body_mass_trend",),
        valid_for_date=as_of.date(),
        as_of=as_of,
    )


def build_goal_assessment(as_of: datetime) -> GoalAssessment:
    return GoalAssessment(
        goal=None,
        data_status=GoalAssessmentDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        valid_for_date=as_of.date(),
        as_of=as_of,
        limitations=("missing_active_goal",),
    )


def build_use_case(
    *,
    weekly_review_workflow,
    context_builder=None,
    context=None,
    athlete=None,
):
    context = context or build_context()
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
    dependencies["health_repository"].load_daily.return_value = [context.today]
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
    dependencies["health_repository"].load_daily.assert_called_once_with()
    weekly_review_workflow.run_with_snapshot.assert_called_once()
    workflow_call = dependencies["intelligence_workflow"].run.call_args
    assert workflow_call.args == (athlete,)
    assert workflow_call.kwargs["snapshot"] is snapshot
    assert workflow_call.kwargs["adaptation"] is result.adaptation
    assert workflow_call.kwargs["body_composition_health_history"] == (
        context.today,
    )
    assert workflow_call.kwargs["nutrition_health_history"] == (
        context.today,
    )
    assert (
        workflow_call.kwargs["body_composition_health_history"]
        is workflow_call.kwargs["nutrition_health_history"]
    )
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


def test_use_case_preserves_canonical_body_composition_assessment_identity():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
        context=context,
    )
    assessment = build_body_composition_assessment(
        datetime.combine(context.today.date, datetime.min.time())
    )
    intelligence = replace(
        dependencies["intelligence_workflow"].run.return_value,
        body_composition=assessment,
    )
    dependencies["intelligence_workflow"].run.return_value = intelligence
    original = deepcopy(assessment)

    result = use_case.run()

    assert result.body_composition is assessment
    assert result.body_composition is intelligence.body_composition
    assert result.body_composition.data_status is (
        BodyCompositionDataStatus.INSUFFICIENT_DATA
    )
    assert result.body_composition.profile == BodyCompositionProfile()
    assert assessment == original
    with pytest.raises(FrozenInstanceError):
        result.body_composition = None
    assert not hasattr(result.report, "body_composition")


def test_use_case_preserves_compatibility_when_workflow_has_no_assessment():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, _, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
        context=context,
    )

    result = use_case.run()

    assert result.body_composition is None
    assert result.goal_assessment is None
    assert result.body_mass_trend_quality is None


def test_use_case_transports_adaptive_assessments_without_copying():
    context = build_context()
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
        context=context,
    )
    as_of = datetime.combine(context.today.date, datetime.min.time())
    quality = build_body_mass_trend_quality(as_of)
    assessment = build_goal_assessment(as_of)
    intelligence = replace(
        dependencies["intelligence_workflow"].run.return_value,
        body_mass_trend_quality=quality,
        goal_assessment=assessment,
    )
    dependencies["intelligence_workflow"].run.return_value = intelligence

    result = use_case.run()

    assert result.goal_assessment is intelligence.goal_assessment is assessment
    assert (
        result.body_mass_trend_quality
        is intelligence.body_mass_trend_quality
        is quality
    )
    assert not hasattr(result.report, "goal_assessment")
    assert not hasattr(result.report, "body_mass_trend_quality")


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


def test_presenter_does_not_interpret_or_present_body_composition():
    source = inspect.getsource(MorningCoachPresenter)

    assert "body_composition" not in source
    assert "BodyCompositionAssessment" not in source
    assert "goal_assessment" not in source
    assert "body_mass_trend_quality" not in source
    assert "AthleteGoal" not in source


def test_use_case_contains_no_alternative_decision_or_recommendation_pipeline():
    source = inspect.getsource(morning_coach_use_case_module)

    assert "DecisionEngine" not in source
    assert "RecommendationEngine" not in source
    assert "NutritionEngine" not in source
    assert "BodyCompositionEngine" not in source
    assert "BodyCompositionInputBuilder" not in source
    assert "DecisionExplainabilityBuilder" not in source
    assert "ExplanationBuilder" not in source
    assert "AthleteGoalReader" not in source
    assert "BodyMassTrendQualityEvaluator" not in source
    assert "GoalAssessmentEngine" not in source


class RecordingIntelligenceWorkflow:
    def __init__(self) -> None:
        self.workflow = build_intelligence_decision_workflow()
        self.results = []

    def run(self, *args, **kwargs):
        result = self.workflow.run(*args, **kwargs)
        self.results.append(result)
        return result


def build_canonical_use_case(*, context, athlete):
    weekly_review_workflow = Mock()
    weekly_review_workflow.run_with_snapshot.return_value = (
        build_snapshot(context),
        build_review(context),
    )
    use_case, dependencies, _, _, _, _ = build_use_case(
        weekly_review_workflow=weekly_review_workflow,
        context=context,
        athlete=athlete,
    )
    recording_workflow = RecordingIntelligenceWorkflow()
    use_case.intelligence_workflow = recording_workflow
    use_case.planner_engine = PlannerEngine()
    dependencies["recovery_engine"].analyze.return_value = athlete.recovery
    return use_case, recording_workflow


def test_canonical_morning_coach_handles_a_neutral_day_end_to_end():
    context = build_context(sleep=480)
    athlete = build_athlete(recovery_score=80, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )

    result = use_case.run()
    intelligence = workflow.results[0]

    assert tuple(
        recommendation.type
        for recommendation in intelligence.recommendations.recommendations
    ) == (RecommendationType.INCREASE_HYDRATION,)
    assert intelligence.explainability.recommendations == (
        "Increase hydration.",
    )
    assert intelligence.nutrition is not None
    assert intelligence.body_composition is not None
    assert result.body_composition is intelligence.body_composition
    assert result.goal_assessment is intelligence.goal_assessment
    assert result.goal_assessment is not None
    assert result.goal_assessment.data_status is (
        GoalAssessmentDataStatus.INSUFFICIENT_DATA
    )
    assert result.body_mass_trend_quality is (
        intelligence.body_mass_trend_quality
    )
    assert result.body_mass_trend_quality is not None
    assert result.body_composition.data_status is (
        BodyCompositionDataStatus.INSUFFICIENT_DATA
    )
    assert result.body_composition.profile == BodyCompositionProfile()
    assert result.decision is intelligence.plan
    assert result.report.explanation.summary == intelligence.explainability.summary
    assert not hasattr(result.report, "body_composition")


def test_canonical_morning_coach_exposes_nutrition_recommendations_in_explainability():
    context = build_context(sleep=480)
    context.today.weight = 80.0
    context.today.resting_energy = 1800
    context.today.active_energy = 700
    athlete = build_athlete(recovery_score=80, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )

    result = use_case.run()
    intelligence = workflow.results[0]

    assert intelligence.nutrition is not None
    assert intelligence.nutrition.data_status.value == "complete"
    assert result.body_composition is intelligence.body_composition
    assert result.body_composition is not None
    assert result.body_composition.profile.body_mass is not None
    assert result.body_composition.profile.body_mass.value == 80.0
    assert result.body_composition.body_mass_trend is None
    assert tuple(
        recommendation.type
        for recommendation in intelligence.recommendations.recommendations
    ) == (
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.INCREASE_CARBOHYDRATE_INTAKE,
    )
    assert intelligence.explainability.recommendations == (
        "Increase hydration.",
        "Increase carbohydrate intake.",
    )
    assert result.report.explanation.reasons == (
        intelligence.explainability.contributing_factors
        + intelligence.explainability.recommendations
    )


def test_canonical_morning_coach_handles_low_recovery_end_to_end():
    context = build_context(sleep=480)
    athlete = build_athlete(recovery_score=60, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )

    result = use_case.run()
    intelligence = workflow.results[0]

    assert intelligence.decision.recommendation is WorkoutType.RECOVERY
    assert tuple(
        recommendation.type
        for recommendation in intelligence.recommendations.recommendations
    ) == (
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
        RecommendationType.INCREASE_HYDRATION,
    )
    assert result.report.explanation.reasons == (
        intelligence.explainability.contributing_factors
        + intelligence.explainability.recommendations
    )


def test_canonical_morning_coach_preserves_a_stale_body_mass_assessment():
    context = build_context(sleep=480)
    athlete = build_athlete(recovery_score=80, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )
    stale = HealthDaily(
        context.today.date - timedelta(days=31),
        weight=81.0,
    )
    use_case.health_repository.load_daily.return_value = [stale, context.today]

    result = use_case.run()
    intelligence = workflow.results[0]

    assert result.body_composition is intelligence.body_composition
    assert result.body_composition is not None
    assert result.body_composition.data_status is (
        BodyCompositionDataStatus.INSUFFICIENT_DATA
    )
    assert result.body_composition.profile.body_mass is None
    assert "stale_body_mass" in result.body_composition.limitations
    use_case.health_repository.load_daily.assert_called_once_with()


def test_canonical_morning_coach_preserves_the_full_body_mass_trend():
    context = build_context(sleep=480)
    context.today.weight = 80.0
    athlete = build_athlete(recovery_score=80, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )
    baseline = HealthDaily(
        context.today.date - timedelta(days=28),
        weight=81.0,
    )
    use_case.health_repository.load_daily.return_value = [
        baseline,
        context.today,
    ]

    result = use_case.run()
    intelligence = workflow.results[0]

    assert result.body_composition is intelligence.body_composition
    assert result.body_composition is not None
    assert result.body_composition.body_mass_trend is not None
    assert result.body_composition.body_mass_trend.period_days == 28
    assert result.body_composition.body_mass_trend.absolute_change_kg == -1.0
    use_case.health_repository.load_daily.assert_called_once_with()


def test_canonical_morning_coach_is_deterministic_with_sleep_debt_and_many_rules():
    context = build_context(sleep=360)
    context.sleep.average_7 = 420
    context.sleep.delta = -60
    context.sleep.delta_percent = (-60 / 420) * 100
    context.hrv.today = 65
    context.hrv.average_7 = 70
    context.hrv.delta = -5
    context.hrv.delta_percent = (-5 / 70) * 100
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=20)
    use_case, workflow = build_canonical_use_case(
        context=context,
        athlete=athlete,
    )

    first = use_case.run()
    second = use_case.run()
    first_intelligence, second_intelligence = workflow.results

    assert first_intelligence == second_intelligence
    assert first == second
    assert first.body_composition is first_intelligence.body_composition
    assert second.body_composition is second_intelligence.body_composition
    assert first.body_composition == second.body_composition
    assert tuple(
        recommendation.type
        for recommendation in first_intelligence.recommendations.recommendations
    ) == (
        RecommendationType.EXTEND_SLEEP,
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.PERFORM_MOBILITY,
    )
    assert (
        first_intelligence.recommendations.recommendations
        == second_intelligence.recommendations.recommendations
    )
    assert tuple(
        recommendation.id
        for recommendation in first_intelligence.recommendations.recommendations
    ) == tuple(
        recommendation.id
        for recommendation in second_intelligence.recommendations.recommendations
    )
    assert "Extend sleep duration." in first.report.explanation.reasons
    assert "Increase hydration." in first.report.explanation.reasons


def test_public_application_exports_are_available():
    assert MorningCoachUseCase.__name__ == "MorningCoachUseCase"
    assert MorningCoachResult.__name__ == "MorningCoachResult"
