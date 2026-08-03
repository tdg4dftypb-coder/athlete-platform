from datetime import date, datetime, timedelta, timezone

import pytest

from adaptive import (
    ActiveGoalSelector,
    AthleteGoal,
    AthleteGoalReader,
    AthleteGoalType,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _goal(
    goal_id: str = "goal-1",
    *,
    valid_from: date = date(2026, 8, 1),
    valid_until: date | None = None,
    recorded_at: datetime = datetime(2026, 8, 1, 6),
    goal_type: AthleteGoalType = AthleteGoalType.REDUCE_BODY_MASS,
    target_body_mass_kg: float | None = 75.0,
) -> AthleteGoal:
    return AthleteGoal(
        id=goal_id,
        goal_type=goal_type,
        valid_from=valid_from,
        recorded_at=recorded_at,
        target_body_mass_kg=target_body_mass_kg,
        valid_until=valid_until,
        evidence=(f"athlete_goal:{goal_id}",),
    )


def test_goal_reader_is_a_structural_read_port():
    class FakeGoalReader:
        def load_active_goal(self, *, valid_for_date, as_of):
            return _goal()

    reader = FakeGoalReader()

    assert isinstance(reader, AthleteGoalReader)
    assert reader.load_active_goal(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) == _goal()


def test_selector_returns_none_when_no_goal_is_available():
    assert ActiveGoalSelector().select(
        (),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None


def test_selector_returns_the_same_active_goal_object():
    goal = _goal()

    selected = ActiveGoalSelector().select(
        (goal,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert selected is goal


def test_selector_excludes_expired_and_future_goals():
    expired = _goal(valid_until=date(2026, 8, 9))
    future = _goal(valid_from=date(2026, 8, 11))

    selector = ActiveGoalSelector()

    assert selector.select(
        (expired,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None
    assert selector.select(
        (future,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None


def test_open_ended_goal_and_validity_boundaries_are_inclusive():
    starts_today = _goal(valid_from=VALID_FOR_DATE)
    ends_today = _goal(
        valid_from=date(2026, 8, 1),
        valid_until=VALID_FOR_DATE,
    )

    selector = ActiveGoalSelector()

    assert selector.select(
        (starts_today,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is starts_today
    assert selector.select(
        (ends_today,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is ends_today


def test_goal_recorded_after_as_of_is_not_yet_available():
    goal = _goal(recorded_at=AS_OF + timedelta(seconds=1))

    assert ActiveGoalSelector().select(
        (goal,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is None


def test_overlapping_active_goals_raise_regardless_of_input_order():
    first = _goal("goal-1")
    second = _goal("goal-2")
    selector = ActiveGoalSelector()

    for goals in ((first, second), (second, first)):
        with pytest.raises(ValueError, match="multiple active athlete goals"):
            selector.select(
                goals,
                valid_for_date=VALID_FOR_DATE,
                as_of=AS_OF,
            )


def test_non_overlapping_result_is_independent_of_input_order():
    active = _goal("active")
    expired = _goal("expired", valid_until=date(2026, 8, 9))
    selector = ActiveGoalSelector()

    assert selector.select(
        (active, expired),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is active
    assert selector.select(
        (expired, active),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is active


def test_selector_rejects_invalid_goal_date_range_and_empty_id():
    selector = ActiveGoalSelector()

    with pytest.raises(ValueError, match="valid_until cannot be before"):
        selector.select(
            (_goal(valid_until=date(2026, 7, 31)),),
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )
    with pytest.raises(ValueError, match="goal id cannot be empty"):
        selector.select(
            (_goal("  "),),
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )


@pytest.mark.parametrize("value", (True, "75", object()))
def test_selector_rejects_non_numeric_target_body_mass(value):
    with pytest.raises(TypeError, match="target_body_mass_kg must be a number"):
        ActiveGoalSelector().select(
            (_goal(target_body_mass_kg=value),),
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )


@pytest.mark.parametrize("value", (0.0, -1.0, float("nan"), float("inf")))
def test_selector_rejects_non_positive_or_non_finite_target_body_mass(value):
    with pytest.raises(ValueError):
        ActiveGoalSelector().select(
            (_goal(target_body_mass_kg=value),),
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )


def test_reduce_body_mass_goal_may_defer_a_missing_target_to_assessment():
    goal = _goal(target_body_mass_kg=None)

    assert ActiveGoalSelector().select(
        (goal,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    ) is goal


def test_selector_rejects_mixed_naive_and_aware_temporal_contracts():
    aware_as_of = AS_OF.replace(tzinfo=timezone.utc)
    aware_goal = _goal(recorded_at=aware_as_of - timedelta(days=1))

    with pytest.raises(ValueError, match="compatible timezones"):
        ActiveGoalSelector().select(
            (_goal(),),
            valid_for_date=VALID_FOR_DATE,
            as_of=aware_as_of,
        )
    with pytest.raises(ValueError, match="compatible timezones"):
        ActiveGoalSelector().select(
            (aware_goal,),
            valid_for_date=VALID_FOR_DATE,
            as_of=AS_OF,
        )


def test_selector_rejects_valid_date_after_as_of():
    with pytest.raises(ValueError, match="valid_for_date cannot be after as_of"):
        ActiveGoalSelector().select(
            (_goal(),),
            valid_for_date=date(2026, 8, 11),
            as_of=AS_OF,
        )


def test_selector_does_not_mutate_goals_or_evidence():
    goal = _goal()
    goals = (goal,)
    original_evidence = goal.evidence

    ActiveGoalSelector().select(
        goals,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert goals == (goal,)
    assert goal.evidence is original_evidence
