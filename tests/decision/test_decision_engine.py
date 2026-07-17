from decision.engine import DecisionEngine
from decision.models import DecisionState
from workout.enums import WorkoutType


def test_recovery_rule_returns_recovery_workout():

    state = DecisionState(
        recovery=20,
        fatigue=70,
        sleep_score=50,
        hrv_score=40,
        resting_hr=55,
        available_minutes=60,
    )

    plan = DecisionEngine().evaluate(state)

    assert plan.recommendation == WorkoutType.RECOVERY