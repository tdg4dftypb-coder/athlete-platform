from unittest.mock import Mock

import application.composition as composition

from application.composition import (
    build_decision_engine,
    build_intelligence_decision_workflow,
    build_morning_coach_use_case,
    build_planner_engine,
    build_recommendation_engine,
    build_weekly_review_workflow,
)
from application.intelligence_decision_workflow import IntelligenceDecisionWorkflow
from application.morning_coach_use_case import MorningCoachUseCase
from application.weekly_review import WeeklyReviewWorkflow
from decision.engine import DecisionEngine
from planner.engine import PlannerEngine
from recommendation import (
    HydrationRecommendationRule,
    MobilityRecommendationRule,
    RecommendationBuilder,
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
    )
    assert isinstance(engine._builder, RecommendationBuilder)


def test_build_intelligence_workflow_injects_ready_dependencies():
    workflow = build_intelligence_decision_workflow()

    assert isinstance(workflow, IntelligenceDecisionWorkflow)
    assert isinstance(workflow.decision_engine, DecisionEngine)
    assert isinstance(workflow.recommendation_engine, RecommendationEngine)


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
        build_intelligence_decision_workflow as public_intelligence_factory,
        build_morning_coach_use_case as public_morning_factory,
        build_recommendation_engine as public_recommendation_factory,
    )

    assert public_intelligence_factory is build_intelligence_decision_workflow
    assert public_morning_factory is build_morning_coach_use_case
    assert public_recommendation_factory is build_recommendation_engine
