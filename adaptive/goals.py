from datetime import date, datetime
from math import isfinite

from adaptive.models import AthleteGoal, AthleteGoalType


class ActiveGoalSelector:
    """Select one temporally active goal from already-loaded domain facts."""

    def select(
        self,
        goals: tuple[AthleteGoal, ...],
        *,
        valid_for_date: date,
        as_of: datetime,
    ) -> AthleteGoal | None:
        self._validate_input(goals, valid_for_date, as_of)

        active_goals = tuple(
            goal
            for goal in goals
            if goal.valid_from <= valid_for_date
            and (goal.valid_until is None or valid_for_date <= goal.valid_until)
            and goal.recorded_at <= as_of
        )
        if len(active_goals) > 1:
            raise ValueError("multiple active athlete goals")

        return active_goals[0] if active_goals else None

    @classmethod
    def _validate_input(
        cls,
        goals: tuple[AthleteGoal, ...],
        valid_for_date: date,
        as_of: datetime,
    ) -> None:
        if not isinstance(goals, tuple):
            raise TypeError("goals must be a tuple")
        if isinstance(valid_for_date, datetime) or not isinstance(
            valid_for_date,
            date,
        ):
            raise TypeError("valid_for_date must be a date")
        if not isinstance(as_of, datetime):
            raise TypeError("as_of must be a datetime")
        if valid_for_date > as_of.date():
            raise ValueError("valid_for_date cannot be after as_of")

        for goal in goals:
            cls._validate_goal(goal, as_of)

    @classmethod
    def _validate_goal(cls, goal: AthleteGoal, as_of: datetime) -> None:
        if not isinstance(goal, AthleteGoal):
            raise TypeError("goals must contain AthleteGoal instances")
        if not isinstance(goal.id, str) or not goal.id.strip():
            raise ValueError("goal id cannot be empty")
        if not isinstance(goal.goal_type, AthleteGoalType):
            raise TypeError("goal_type must be an AthleteGoalType")
        if isinstance(goal.valid_from, datetime) or not isinstance(
            goal.valid_from,
            date,
        ):
            raise TypeError("valid_from must be a date")
        if goal.valid_until is not None and (
            isinstance(goal.valid_until, datetime)
            or not isinstance(goal.valid_until, date)
        ):
            raise TypeError("valid_until must be a date or None")
        if (
            goal.valid_until is not None
            and goal.valid_until < goal.valid_from
        ):
            raise ValueError("valid_until cannot be before valid_from")
        if not isinstance(goal.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")

        cls._validate_compatible_timezones(goal.recorded_at, as_of)
        cls._validate_target_body_mass(goal.target_body_mass_kg)

    @staticmethod
    def _validate_target_body_mass(value: float | None) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("target_body_mass_kg must be a number")
        if not isfinite(value):
            raise ValueError("target_body_mass_kg must be finite")
        if value <= 0.0:
            raise ValueError("target_body_mass_kg must be positive")

    @staticmethod
    def _validate_compatible_timezones(
        recorded_at: datetime,
        as_of: datetime,
    ) -> None:
        recorded_is_aware = (
            recorded_at.tzinfo is not None
            and recorded_at.utcoffset() is not None
        )
        as_of_is_aware = as_of.tzinfo is not None and as_of.utcoffset() is not None
        if recorded_is_aware != as_of_is_aware:
            raise ValueError("recorded_at and as_of must use compatible timezones")
