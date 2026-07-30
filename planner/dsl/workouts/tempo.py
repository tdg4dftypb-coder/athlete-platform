from planner.dsl.models import (
    Interval,
    Repeat,
    Workout,
)


def tempo() -> Workout:

    return Workout(
        name="Tempo Ride",
        children=[
            Interval(
                name="Warmup",
                duration=15 * 60,
                power_from=0.50,
                power_to=0.70,
                cadence_from=85,
                cadence_to=95,
            ),
            Repeat(
                count=3,
                children=[
                    Interval(
                        name="Tempo",
                        duration=20 * 60,
                        power_from=0.80,
                        power_to=0.88,
                        cadence_from=90,
                        cadence_to=100,
                    ),
                    Interval(
                        name="Recovery",
                        duration=5 * 60,
                        power_from=0.50,
                        power_to=0.60,
                        cadence_from=85,
                        cadence_to=95,
                    ),
                ],
            ),
            Interval(
                name="Cooldown",
                duration=15 * 60,
                power_from=0.45,
                power_to=0.60,
                cadence_from=80,
                cadence_to=90,
            ),
        ],
    )