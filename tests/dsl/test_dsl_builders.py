from planner.dsl.workouts import (
    endurance,
    recovery,
    threshold,
    vo2,
)


def test_recovery_duration():

    workout = recovery(
        45,
        25,
    )

    block = workout.children[0]

    assert block.duration == 45 * 60

    assert workout.target_tss == 25


def test_endurance_duration():

    workout = endurance(
        120,
        65,
    )

    block = workout.children[0]

    assert block.duration == 120 * 60

    assert workout.target_tss == 65


def test_threshold_build():

    workout = threshold(
        90,
        80,
    )

    assert workout.name == "Threshold"

    assert workout.target_tss == 80

    assert len(workout.children) == 3


def test_vo2_build():

    workout = vo2(
        75,
        85,
    )

    assert workout.name == "VO2 Max"

    assert workout.target_tss == 85

    assert len(workout.children) == 3