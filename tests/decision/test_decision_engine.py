from decision.engine import DecisionEngine

from tests.helpers import build_athlete

from workout.enums import WorkoutType


def test_recovery_rule_returns_recovery_workout():

    athlete = build_athlete(
        recovery_score=20,
        fatigue=70,
    )

    plan = DecisionEngine().decide(athlete)

    assert plan.recommendation == WorkoutType.RECOVERY