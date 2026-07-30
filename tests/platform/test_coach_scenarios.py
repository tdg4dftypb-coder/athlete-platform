from pipeline.engine import PlatformEngine

from tests.helpers import build_athlete


def test_fresh_athlete_gets_high_intensity_workout():

    athlete = build_athlete(
        recovery_score=90,
        fatigue=20,
        freshness=80,
    )

    result = PlatformEngine().run(
        athlete,
    )

    plan = result["plan"]

    workout = result["workout"]

    assert plan.recommendation.value == "vo2"

    assert workout.blocks

    assert workout.target_tss > 0

    assert workout.estimated_duration > 0



def test_normal_athlete_gets_threshold_or_endurance():

    athlete = build_athlete(
        recovery_score=70,
        fatigue=30,
        freshness=30,
    )

    result = PlatformEngine().run(
        athlete,
    )

    plan = result["plan"]

    workout = result["workout"]

    assert plan.recommendation.value in (
        "threshold",
        "endurance",
    )

    assert workout.blocks



def test_fatigued_athlete_gets_recovery():

    athlete = build_athlete(
        recovery_score=30,
        fatigue=80,
        freshness=-20,
    )

    result = PlatformEngine().run(
        athlete,
    )

    plan = result["plan"]

    workout = result["workout"]

    assert plan.recommendation.value == "recovery"

    assert workout.blocks

    assert workout.target_tss > 0