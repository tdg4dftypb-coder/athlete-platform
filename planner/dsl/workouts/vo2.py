from planner.dsl.models import (
    Interval,
    Repeat,
    Workout,
    WorkoutPrescription,
)


def build(
    duration: int,
    target_tss: float = 0,
) -> Workout:

    return Workout(
        name="VO2 Max",
        prescription=WorkoutPrescription(
            duration=duration,
            target_tss=target_tss,
        ),
        children=[
            Interval(
                name="Warmup",
                duration=15 * 60,
                power_from=0.55,
                power_to=0.75,
                cadence_from=85,
                cadence_to=95,
            ),
            Repeat(
                count=5,
                children=[
                    Interval(
                        name="Work",
                        duration=5 * 60,
                        power_from=1.08,
                        power_to=1.15,
                        cadence_from=90,
                        cadence_to=100,
                    ),
                    Interval(
                        name="Recovery",
                        duration=5 * 60,
                        power_from=0.50,
                        power_to=0.60,
                        cadence_from=80,
                        cadence_to=90,
                    ),
                ],
            ),
            Interval(
                name="Cooldown",
                duration=10 * 60,
                power_from=0.45,
                power_to=0.55,
                cadence_from=80,
                cadence_to=90,
            ),
        ],
    )