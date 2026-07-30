import pytest

from pipeline.engine import PlatformEngine

from tests.helpers import build_athlete

from workout.enums import WorkoutType


@pytest.mark.parametrize(
    (
        "recovery_score",
        "fatigue",
        "freshness",
        "expected",
    ),
    [
        (
            20,
            70,
            0,
            WorkoutType.RECOVERY,
        ),
        (
            60,
            50,
            0,
            WorkoutType.ENDURANCE,
        ),
        (
            80,
            30,
            0,
            WorkoutType.THRESHOLD,
        ),
        (
            90,
            20,
            80,
            WorkoutType.VO2,
        ),
    ],
)
def test_platform_engine_builds_workout(
    recovery_score: int,
    fatigue: float,
    freshness: float,
    expected: WorkoutType,
):

    athlete = build_athlete(
        recovery_score=recovery_score,
        fatigue=fatigue,
        freshness=freshness,
    )

    result = PlatformEngine().run(
        athlete,
    )

    assert (
        result["plan"].recommendation
        == expected
    )

    workout = result["workout"]

    simulation = result["simulation"]

    assert workout.blocks

    assert workout.target_tss > 0

    assert simulation.duration > 0

    assert simulation.tss > 0

    assert (
        simulation.tss
        ==
        workout.target_tss
    )

    assert result["timeline"] is not None