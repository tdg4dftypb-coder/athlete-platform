from planner.dsl.models import (
    Interval,
    Workout,
    WorkoutPrescription,
)


def build(
    duration: int,
    target_tss: float = 0,
) -> Workout:

    return Workout(
        name="Endurance",
        prescription=WorkoutPrescription(
            duration=duration,
            target_tss=target_tss,
        ),
        children=[
            Interval(
                name="Endurance Ride",
                duration=duration * 60,
                power_from=0.60,
                power_to=0.70,
                cadence_from=85,
                cadence_to=95,
            ),
        ],
    )