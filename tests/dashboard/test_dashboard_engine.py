from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from itertools import product

import pytest

from adaptive import GoalAssessment, GoalAssessmentDataStatus
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionProfile,
)
from dashboard import (
    AthleteDashboard,
    DashboardEngine,
    DashboardSection,
    DashboardSectionStatus,
)
from decision.models import DecisionResult
from decision.sports import Sport
from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
)
from recommendation import (
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from workout.enums import WorkoutType


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6)


def _decision() -> DecisionResult:
    return DecisionResult(
        sport=Sport.CYCLING,
        recommendation=WorkoutType.ENDURANCE,
        duration=60,
        target_tss=50.0,
        intensity="endurance",
        reasons=[],
    )


def _body_composition(
    status: BodyCompositionDataStatus,
    confidence: float = 0.625,
) -> BodyCompositionAssessment:
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=status,
        confidence=confidence,
        evidence=("body:2026-08-03",),
        limitations=("missing_body_fat",),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _nutrition(
    status: NutritionDataStatus,
    confidence: float = 0.75,
) -> NutritionAssessment:
    return NutritionAssessment(
        energy_requirement=EnergyRequirement(),
        macro_targets=MacroTargets(),
        fueling_plan=FuelingPlan(),
        hydration_target=HydrationTarget(),
        data_status=status,
        confidence=confidence,
        evidence=("nutrition:2026-08-03",),
        limitations=("missing_energy_intake",),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _goal(
    status: GoalAssessmentDataStatus,
    confidence: float = 0.4,
) -> GoalAssessment:
    return GoalAssessment(
        goal=None,
        data_status=status,
        confidence=confidence,
        evidence=("goal:2026-08-03",),
        limitations=("missing_active_goal",),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _recommendation() -> Recommendation:
    return Recommendation(
        id="recommendation-1",
        type=RecommendationType.INCREASE_HYDRATION,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.8,
        evidence=("nutrition:2026-08-03",),
        source_rules=("NutritionRecommendationRule",),
        as_of=AS_OF,
    )


def _build(
    *,
    decision=None,
    body_composition=None,
    nutrition=None,
    goal=None,
    recommendations=(),
) -> AthleteDashboard:
    return DashboardEngine().build(
        decision=decision,
        body_composition=body_composition,
        nutrition=nutrition,
        goal=goal,
        recommendations=recommendations,
    )


def test_empty_inputs_build_all_unavailable_sections():
    assert _build() == AthleteDashboard(
        decision=DashboardSection(
            "Decision",
            DashboardSectionStatus.UNAVAILABLE,
            0.0,
        ),
        body_composition=DashboardSection(
            "Body Composition",
            DashboardSectionStatus.UNAVAILABLE,
            0.0,
        ),
        nutrition=DashboardSection(
            "Nutrition",
            DashboardSectionStatus.UNAVAILABLE,
            0.0,
        ),
        goal=DashboardSection(
            "Goal",
            DashboardSectionStatus.UNAVAILABLE,
            0.0,
        ),
        recommendations=DashboardSection(
            "Recommendations",
            DashboardSectionStatus.UNAVAILABLE,
            0.0,
        ),
    )


def test_complete_inputs_build_a_fully_ready_dashboard():
    dashboard = _build(
        decision=_decision(),
        body_composition=_body_composition(
            BodyCompositionDataStatus.COMPLETE,
            1.0,
        ),
        nutrition=_nutrition(NutritionDataStatus.COMPLETE, 1.0),
        goal=_goal(GoalAssessmentDataStatus.COMPLETE, 1.0),
        recommendations=(_recommendation(),),
    )

    assert tuple(
        section.status
        for section in (
            dashboard.decision,
            dashboard.body_composition,
            dashboard.nutrition,
            dashboard.goal,
            dashboard.recommendations,
        )
    ) == (DashboardSectionStatus.READY,) * 5
    assert dashboard.decision.confidence == 1.0
    assert dashboard.recommendations.confidence == 1.0


@pytest.mark.parametrize(
    ("source_status", "expected_status"),
    (
        (BodyCompositionDataStatus.COMPLETE, DashboardSectionStatus.READY),
        (BodyCompositionDataStatus.PARTIAL, DashboardSectionStatus.PARTIAL),
        (
            BodyCompositionDataStatus.INSUFFICIENT_DATA,
            DashboardSectionStatus.UNAVAILABLE,
        ),
    ),
)
def test_body_composition_policy_copies_assessment_metadata(
    source_status,
    expected_status,
):
    assessment = _body_composition(source_status)
    section = _build(body_composition=assessment).body_composition

    assert section == DashboardSection(
        title="Body Composition",
        status=expected_status,
        confidence=assessment.confidence,
        evidence=assessment.evidence,
        limitations=assessment.limitations,
    )


@pytest.mark.parametrize(
    ("source_status", "expected_status"),
    (
        (NutritionDataStatus.COMPLETE, DashboardSectionStatus.READY),
        (NutritionDataStatus.PARTIAL, DashboardSectionStatus.PARTIAL),
        (
            NutritionDataStatus.INSUFFICIENT_DATA,
            DashboardSectionStatus.UNAVAILABLE,
        ),
    ),
)
def test_nutrition_policy_copies_assessment_metadata(
    source_status,
    expected_status,
):
    assessment = _nutrition(source_status)
    section = _build(nutrition=assessment).nutrition

    assert section == DashboardSection(
        title="Nutrition",
        status=expected_status,
        confidence=assessment.confidence,
        evidence=assessment.evidence,
        limitations=assessment.limitations,
    )


@pytest.mark.parametrize(
    ("source_status", "expected_status"),
    (
        (GoalAssessmentDataStatus.COMPLETE, DashboardSectionStatus.READY),
        (GoalAssessmentDataStatus.PARTIAL, DashboardSectionStatus.PARTIAL),
        (
            GoalAssessmentDataStatus.INSUFFICIENT_DATA,
            DashboardSectionStatus.UNAVAILABLE,
        ),
    ),
)
def test_goal_policy_copies_assessment_metadata(
    source_status,
    expected_status,
):
    assessment = _goal(source_status)
    section = _build(goal=assessment).goal

    assert section == DashboardSection(
        title="Goal",
        status=expected_status,
        confidence=assessment.confidence,
        evidence=assessment.evidence,
        limitations=assessment.limitations,
    )


def test_decision_and_recommendation_sections_do_not_copy_domain_evidence():
    dashboard = _build(
        decision=_decision(),
        recommendations=(_recommendation(),),
    )

    assert dashboard.decision == DashboardSection(
        "Decision",
        DashboardSectionStatus.READY,
        1.0,
    )
    assert dashboard.recommendations == DashboardSection(
        "Recommendations",
        DashboardSectionStatus.READY,
        1.0,
    )
    assert dashboard.decision.evidence == ()
    assert dashboard.decision.limitations == ()
    assert dashboard.recommendations.evidence == ()
    assert dashboard.recommendations.limitations == ()


def test_dashboard_output_is_immutable():
    dashboard = _build(decision=_decision())

    with pytest.raises(FrozenInstanceError):
        dashboard.decision = None
    with pytest.raises(FrozenInstanceError):
        dashboard.decision.confidence = 0.0


def test_engine_is_deterministic_stateless_and_returns_fresh_projection_identity():
    engine = DashboardEngine()
    arguments = {
        "decision": _decision(),
        "body_composition": _body_composition(
            BodyCompositionDataStatus.PARTIAL
        ),
        "nutrition": _nutrition(NutritionDataStatus.PARTIAL),
        "goal": _goal(GoalAssessmentDataStatus.PARTIAL),
        "recommendations": (_recommendation(),),
    }

    first = engine.build(**arguments)
    second = engine.build(**arguments)

    assert first == second
    assert first is not second
    assert first.decision is not second.decision
    assert first.body_composition is not second.body_composition
    assert vars(engine) == {}


def test_engine_does_not_mutate_any_input():
    decision = _decision()
    body_composition = _body_composition(BodyCompositionDataStatus.PARTIAL)
    nutrition = _nutrition(NutritionDataStatus.PARTIAL)
    goal = _goal(GoalAssessmentDataStatus.PARTIAL)
    recommendations = (_recommendation(),)
    inputs_before = deepcopy(
        (decision, body_composition, nutrition, goal, recommendations)
    )

    _build(
        decision=decision,
        body_composition=body_composition,
        nutrition=nutrition,
        goal=goal,
        recommendations=recommendations,
    )

    assert (decision, body_composition, nutrition, goal, recommendations) == (
        inputs_before
    )


_ASSESSMENT_CASES = (None, "complete", "partial", "insufficient")


@pytest.mark.parametrize(
    (
        "has_decision",
        "body_case",
        "nutrition_case",
        "goal_case",
        "has_recommendations",
    ),
    tuple(
        product(
            (False, True),
            _ASSESSMENT_CASES,
            _ASSESSMENT_CASES,
            _ASSESSMENT_CASES,
            (False, True),
        )
    ),
)
def test_every_section_state_combination_is_independent(
    has_decision,
    body_case,
    nutrition_case,
    goal_case,
    has_recommendations,
):
    body_statuses = {
        "complete": BodyCompositionDataStatus.COMPLETE,
        "partial": BodyCompositionDataStatus.PARTIAL,
        "insufficient": BodyCompositionDataStatus.INSUFFICIENT_DATA,
    }
    nutrition_statuses = {
        "complete": NutritionDataStatus.COMPLETE,
        "partial": NutritionDataStatus.PARTIAL,
        "insufficient": NutritionDataStatus.INSUFFICIENT_DATA,
    }
    goal_statuses = {
        "complete": GoalAssessmentDataStatus.COMPLETE,
        "partial": GoalAssessmentDataStatus.PARTIAL,
        "insufficient": GoalAssessmentDataStatus.INSUFFICIENT_DATA,
    }
    expected = {
        None: DashboardSectionStatus.UNAVAILABLE,
        "complete": DashboardSectionStatus.READY,
        "partial": DashboardSectionStatus.PARTIAL,
        "insufficient": DashboardSectionStatus.UNAVAILABLE,
    }

    dashboard = _build(
        decision=_decision() if has_decision else None,
        body_composition=(
            _body_composition(body_statuses[body_case])
            if body_case is not None
            else None
        ),
        nutrition=(
            _nutrition(nutrition_statuses[nutrition_case])
            if nutrition_case is not None
            else None
        ),
        goal=(
            _goal(goal_statuses[goal_case])
            if goal_case is not None
            else None
        ),
        recommendations=(_recommendation(),) if has_recommendations else (),
    )

    assert dashboard.decision.status is (
        DashboardSectionStatus.READY
        if has_decision
        else DashboardSectionStatus.UNAVAILABLE
    )
    assert dashboard.body_composition.status is expected[body_case]
    assert dashboard.nutrition.status is expected[nutrition_case]
    assert dashboard.goal.status is expected[goal_case]
    assert dashboard.recommendations.status is (
        DashboardSectionStatus.READY
        if has_recommendations
        else DashboardSectionStatus.UNAVAILABLE
    )


def test_dashboard_engine_is_publicly_exported():
    import dashboard
    from dashboard.engine import DashboardEngine as EngineImplementation

    assert dashboard.DashboardEngine is EngineImplementation
