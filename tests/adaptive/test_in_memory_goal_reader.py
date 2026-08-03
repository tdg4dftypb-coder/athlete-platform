from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from adaptive import (
    AthleteGoal,
    AthleteGoalReader,
    AthleteGoalType,
    InMemoryAthleteGoalReader,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _goal(goal_id: str = "goal-1") -> AthleteGoal:
    return AthleteGoal(
        id=goal_id,
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=VALID_FOR_DATE,
        recorded_at=AS_OF,
    )


def test_reader_returns_the_same_active_goal_instance():
    goal = _goal()
    reader = InMemoryAthleteGoalReader((goal,))

    result = reader.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert result is goal
    assert isinstance(reader, AthleteGoalReader)


def test_empty_and_inactive_configuration_return_no_goal():
    empty = InMemoryAthleteGoalReader()
    future = InMemoryAthleteGoalReader(
        (
            AthleteGoal(
                id="future",
                goal_type=AthleteGoalType.MAINTAIN,
                valid_from=date(2026, 8, 11),
                recorded_at=AS_OF,
            ),
        )
    )

    assert empty.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None
    assert future.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None


def test_overlapping_active_goals_remain_a_controlled_error():
    reader = InMemoryAthleteGoalReader((_goal("a"), _goal("b")))

    with pytest.raises(ValueError, match="multiple active athlete goals"):
        reader.load_active_goal(
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )


def test_reader_requires_an_immutable_tuple_and_is_frozen():
    with pytest.raises(TypeError, match="tuple"):
        InMemoryAthleteGoalReader([_goal()])

    reader = InMemoryAthleteGoalReader((_goal(),))
    with pytest.raises(FrozenInstanceError):
        reader.goals = ()


def test_reader_is_deterministic_and_has_no_mutable_global_state():
    goal = _goal()
    reader = InMemoryAthleteGoalReader((goal,))

    first = reader.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )
    second = reader.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert first is second is goal
