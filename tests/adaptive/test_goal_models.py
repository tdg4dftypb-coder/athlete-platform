from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime

import pytest

from adaptive import (
    AthleteGoal,
    AthleteGoalType,
    GoalAssessment,
    GoalAssessmentDataStatus,
)


VALID_FROM = date(2026, 8, 3)
VALID_FOR_DATE = date(2026, 8, 10)
RECORDED_AT = datetime(2026, 8, 3, 6, 0)
AS_OF = datetime(2026, 8, 10, 6, 0)


def _goal() -> AthleteGoal:
    return AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.REDUCE_BODY_MASS,
        valid_from=VALID_FROM,
        recorded_at=RECORDED_AT,
        target_body_mass_kg=75.0,
        valid_until=date(2026, 12, 31),
        evidence=("athlete_goal:goal-1",),
    )


def _assessment() -> GoalAssessment:
    return GoalAssessment(
        goal=_goal(),
        data_status=GoalAssessmentDataStatus.PARTIAL,
        confidence=0.5,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        evidence=("athlete_goal:goal-1", "body_mass:2026-08-10"),
        limitations=("insufficient_body_mass_history",),
    )


@pytest.mark.parametrize(
    "model, attribute, value",
    (
        (_goal(), "target_body_mass_kg", 74.0),
        (_assessment(), "confidence", 1.0),
    ),
)
def test_adaptive_goal_models_are_immutable(model, attribute, value):
    with pytest.raises(FrozenInstanceError):
        setattr(model, attribute, value)


def test_adaptive_goal_models_are_frozen_dataclasses():
    assert is_dataclass(AthleteGoal)
    assert is_dataclass(GoalAssessment)
    assert AthleteGoal.__dataclass_params__.frozen is True
    assert GoalAssessment.__dataclass_params__.frozen is True


def test_collection_fields_use_immutable_tuples():
    goal = _goal()
    assessment = _assessment()

    assert isinstance(goal.evidence, tuple)
    assert isinstance(assessment.evidence, tuple)
    assert isinstance(assessment.limitations, tuple)


def test_goal_type_contains_only_the_mvp_contract():
    assert tuple(AthleteGoalType) == (
        AthleteGoalType.MAINTAIN,
        AthleteGoalType.REDUCE_BODY_MASS,
    )
    assert tuple(goal_type.value for goal_type in AthleteGoalType) == (
        "maintain",
        "reduce_body_mass",
    )


def test_goal_assessment_data_status_matches_existing_assessment_semantics():
    assert tuple(GoalAssessmentDataStatus) == (
        GoalAssessmentDataStatus.COMPLETE,
        GoalAssessmentDataStatus.PARTIAL,
        GoalAssessmentDataStatus.INSUFFICIENT_DATA,
    )
    assert tuple(status.value for status in GoalAssessmentDataStatus) == (
        "complete",
        "partial",
        "insufficient_data",
    )


def test_public_package_exports_the_stage_9_2_domain_contract():
    assert AthleteGoal.__module__ == "adaptive.models"
    assert AthleteGoalType.__module__ == "adaptive.models"
    assert GoalAssessment.__module__ == "adaptive.models"
    assert GoalAssessmentDataStatus.__module__ == "adaptive.models"


def test_goal_optional_fields_have_domain_safe_defaults():
    goal = AthleteGoal(
        id="goal-2",
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=VALID_FROM,
        recorded_at=RECORDED_AT,
    )

    assert goal.target_body_mass_kg is None
    assert goal.valid_until is None
    assert goal.evidence == ()


def test_assessment_collection_fields_default_to_empty_tuples():
    assessment = GoalAssessment(
        goal=_goal(),
        data_status=GoalAssessmentDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert assessment.evidence == ()
    assert assessment.limitations == ()


def test_models_have_value_equality_and_deterministic_repr():
    assert _goal() == _goal()
    assert _assessment() == _assessment()
    assert repr(_goal()) == repr(_goal())
    assert repr(_assessment()) == repr(_assessment())


def test_models_are_hashable():
    assert hash(_goal()) == hash(_goal())
    assert hash(_assessment()) == hash(_assessment())
    assert {_goal(), _goal()} == {_goal()}


def test_tuple_values_cannot_be_mutated_through_the_models():
    goal = _goal()
    assessment = _assessment()

    with pytest.raises(TypeError):
        goal.evidence[0] = "changed"
    with pytest.raises(TypeError):
        assessment.evidence[0] = "changed"
    with pytest.raises(TypeError):
        assessment.limitations[0] = "changed"


def test_models_contain_only_the_accepted_stage_9_2_fields():
    assert tuple(field.name for field in fields(AthleteGoal)) == (
        "id",
        "goal_type",
        "valid_from",
        "recorded_at",
        "target_body_mass_kg",
        "valid_until",
        "evidence",
    )
    assert tuple(field.name for field in fields(GoalAssessment)) == (
        "goal",
        "data_status",
        "confidence",
        "valid_for_date",
        "as_of",
        "evidence",
        "limitations",
    )
