from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import application.composition as composition

from adaptive import (
    AdaptiveGoalRecommendationRule,
    AthleteGoal,
    AthleteGoalType,
    BodyMassTrendQualityEvaluator,
    GoalAssessment,
    GoalAssessmentDataStatus,
    GoalAssessmentEngine,
    InMemoryAthleteGoalReader,
)
from application.body_mass_trend_quality_input import (
    BodyMassTrendQualityInputBuilder,
)
from application.body_composition_input import BodyCompositionInputBuilder
from application.composition import (
    build_athlete_goal_reader,
    build_body_mass_trend_quality_evaluator,
    build_decision_engine,
    build_goal_assessment_engine,
    build_intelligence_decision_workflow,
    build_morning_coach_use_case,
    build_planner_engine,
    build_recommendation_engine,
    build_weekly_review_workflow,
)
from application.intelligence_decision_workflow import IntelligenceDecisionWorkflow
from application.morning_coach_use_case import MorningCoachUseCase
from application.nutrition_input import NutritionInputBuilder
from application.weekly_review import WeeklyReviewWorkflow
from body_composition import BodyCompositionEngine
from decision.engine import DecisionEngine
from nutrition import NutritionEngine, NutritionRecommendationRule
from planner.engine import PlannerEngine
from recommendation import (
    HydrationRecommendationRule,
    MobilityRecommendationRule,
    RecommendationBuilder,
    RecommendationContext,
    RecommendationEngine,
    RecoveryRecommendationRule,
    SleepRecommendationRule,
)


def test_build_recommendation_engine_uses_the_canonical_configuration():
    engine = build_recommendation_engine()

    assert isinstance(engine, RecommendationEngine)
    assert tuple(type(rule) for rule in engine._rules) == (
        SleepRecommendationRule,
        HydrationRecommendationRule,
        RecoveryRecommendationRule,
        MobilityRecommendationRule,
        NutritionRecommendationRule,
        AdaptiveGoalRecommendationRule,
    )
    assert isinstance(engine._builder, RecommendationBuilder)


def test_canonical_engine_runs_nutrition_rule_once():
    engine = build_recommendation_engine()
    nutrition_rule = next(
        rule
        for rule in engine._rules
        if isinstance(rule, NutritionRecommendationRule)
    )
    nutrition_rule.evaluate = Mock(wraps=nutrition_rule.evaluate)
    decision = Mock()
    decision.decision_reasons = ()
    decision.confidence = 0.0
    context = RecommendationContext(
        decision=decision,
        insights=(),
        observations=(),
    )

    engine.evaluate(context)

    nutrition_rule.evaluate.assert_called_once_with(context)


def test_canonical_engine_runs_each_of_six_rules_once():
    engine = build_recommendation_engine()
    context = RecommendationContext(
        decision=SimpleNamespace(decision_reasons=(), confidence=0.0),
        insights=(),
        observations=(),
    )
    for rule in engine._rules:
        rule.evaluate = Mock(wraps=rule.evaluate)

    result = engine.evaluate(context)

    assert result.recommendations == ()
    for rule in engine._rules:
        rule.evaluate.assert_called_once_with(context)


def test_canonical_adaptive_rule_is_order_independent_after_building():
    engine = build_recommendation_engine()
    as_of = datetime(2026, 8, 10, 6)
    goal = AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=date(2026, 8, 10),
        recorded_at=as_of,
    )
    assessment = GoalAssessment(
        goal=goal,
        data_status=GoalAssessmentDataStatus.COMPLETE,
        confidence=1.0,
        valid_for_date=date(2026, 8, 10),
        as_of=as_of,
    )
    context = RecommendationContext(
        decision=SimpleNamespace(decision_reasons=(), confidence=0.0),
        insights=(),
        observations=(),
        goal_assessment=assessment,
    )
    reversed_engine = RecommendationEngine(
        rules=tuple(reversed(engine._rules)),
        builder=RecommendationBuilder(),
    )

    assert engine.evaluate(context) == reversed_engine.evaluate(context)


def test_build_intelligence_workflow_injects_ready_dependencies():
    workflow = build_intelligence_decision_workflow()

    assert isinstance(workflow, IntelligenceDecisionWorkflow)
    assert isinstance(workflow.decision_engine, DecisionEngine)
    assert isinstance(workflow.recommendation_engine, RecommendationEngine)
    assert isinstance(workflow.nutrition_input_builder, NutritionInputBuilder)
    assert isinstance(workflow.nutrition_engine, NutritionEngine)
    assert isinstance(
        workflow.body_composition_input_builder,
        BodyCompositionInputBuilder,
    )
    assert isinstance(workflow.body_composition_engine, BodyCompositionEngine)
    assert isinstance(workflow.athlete_goal_reader, InMemoryAthleteGoalReader)
    assert isinstance(
        workflow.body_mass_trend_quality_input_builder,
        BodyMassTrendQualityInputBuilder,
    )
    assert isinstance(
        workflow.body_mass_trend_quality_evaluator,
        BodyMassTrendQualityEvaluator,
    )
    assert isinstance(workflow.goal_assessment_engine, GoalAssessmentEngine)


def test_build_weekly_review_workflow_uses_the_supplied_database():
    database = Mock()

    workflow = build_weekly_review_workflow(database)

    assert isinstance(workflow, WeeklyReviewWorkflow)
    assert workflow.reader.repository.db is database


def test_build_morning_coach_use_case_preserves_the_current_pipeline():
    database = Mock()
    health_repository = Mock()

    use_case = build_morning_coach_use_case(database, health_repository)

    assert isinstance(use_case, MorningCoachUseCase)
    assert use_case.health_repository is health_repository
    assert isinstance(use_case.weekly_review_workflow, WeeklyReviewWorkflow)
    assert isinstance(use_case.intelligence_workflow, IntelligenceDecisionWorkflow)
    assert not hasattr(use_case, "decision_engine")
    assert isinstance(use_case.planner_engine, PlannerEngine)


def test_small_engine_factories_return_fresh_instances():
    first_decision = build_decision_engine()
    second_decision = build_decision_engine()
    first_planner = build_planner_engine()
    second_planner = build_planner_engine()

    assert isinstance(first_decision, DecisionEngine)
    assert isinstance(first_planner, PlannerEngine)
    assert first_decision is not second_decision
    assert first_planner is not second_planner
    assert build_athlete_goal_reader() is not build_athlete_goal_reader()
    assert (
        build_body_mass_trend_quality_evaluator()
        is not build_body_mass_trend_quality_evaluator()
    )
    assert build_goal_assessment_engine() is not build_goal_assessment_engine()


def test_all_factories_return_fresh_instances():
    database = Mock()
    health_repository = Mock()

    assert build_recommendation_engine() is not build_recommendation_engine()
    assert (
        build_intelligence_decision_workflow()
        is not build_intelligence_decision_workflow()
    )
    assert build_weekly_review_workflow(database) is not build_weekly_review_workflow(
        database
    )
    assert build_morning_coach_use_case(
        database,
        health_repository,
    ) is not build_morning_coach_use_case(database, health_repository)


def test_recommendation_factory_creates_fresh_rules_and_builder():
    first = build_recommendation_engine()
    second = build_recommendation_engine()

    assert first._builder is not second._builder
    assert all(
        first_rule is not second_rule
        for first_rule, second_rule in zip(first._rules, second._rules)
    )


def test_intelligence_workflow_factory_injects_fresh_nutrition_dependencies():
    first = build_intelligence_decision_workflow()
    second = build_intelligence_decision_workflow()

    assert first.nutrition_input_builder is not second.nutrition_input_builder
    assert first.nutrition_engine is not second.nutrition_engine


def test_intelligence_workflow_factory_injects_fresh_body_composition_dependencies():
    first = build_intelligence_decision_workflow()
    second = build_intelligence_decision_workflow()

    assert (
        first.body_composition_input_builder
        is not second.body_composition_input_builder
    )
    assert first.body_composition_engine is not second.body_composition_engine
    assert len(first.recommendation_engine._rules) == 6
    assert all(
        "BodyCompositionRecommendationRule" not in type(rule).__name__
        for rule in first.recommendation_engine._rules
    )


def test_adaptive_factories_use_empty_or_explicit_immutable_goal_configuration():
    as_of = datetime(2026, 8, 10, 6)
    goal = AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=as_of.date(),
        recorded_at=as_of,
    )

    empty_workflow = build_intelligence_decision_workflow()
    configured_workflow = build_intelligence_decision_workflow((goal,))

    assert empty_workflow.athlete_goal_reader.goals == ()
    assert configured_workflow.athlete_goal_reader.goals == (goal,)
    assert configured_workflow.athlete_goal_reader.load_active_goal(
        valid_for_date=as_of.date(),
        as_of=as_of,
    ) is goal
    assert len(configured_workflow.recommendation_engine._rules) == 6


def test_morning_coach_factory_passes_explicit_goals_to_canonical_workflow():
    database = Mock()
    goal = AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=date(2026, 8, 10),
        recorded_at=datetime(2026, 8, 10, 6),
    )

    use_case = build_morning_coach_use_case(
        database,
        Mock(),
        (goal,),
    )

    assert use_case.intelligence_workflow.athlete_goal_reader.goals == (goal,)


def test_default_morning_coach_composition_defers_health_repository_io(
    monkeypatch,
):
    database = Mock()
    repository = Mock()
    repository.load_daily.return_value = []
    repository_factory = Mock(return_value=repository)
    monkeypatch.setattr(composition, "HealthRepository", repository_factory)

    use_case = build_morning_coach_use_case(database)

    repository_factory.assert_not_called()
    assert use_case.health_repository.load_daily() == []
    repository_factory.assert_called_once_with()
    repository.load_daily.assert_called_once_with()


def test_public_application_exports_include_composition_factories():
    from application import (
        build_athlete_goal_reader as public_goal_reader_factory,
        build_body_mass_trend_quality_evaluator as public_quality_factory,
        build_goal_assessment_engine as public_assessment_factory,
        build_intelligence_decision_workflow as public_intelligence_factory,
        build_morning_coach_use_case as public_morning_factory,
        build_recommendation_engine as public_recommendation_factory,
    )

    assert public_intelligence_factory is build_intelligence_decision_workflow
    assert public_morning_factory is build_morning_coach_use_case
    assert public_recommendation_factory is build_recommendation_engine
    assert public_goal_reader_factory is build_athlete_goal_reader
    assert public_quality_factory is build_body_mass_trend_quality_evaluator
    assert public_assessment_factory is build_goal_assessment_engine
