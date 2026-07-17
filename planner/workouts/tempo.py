from planner.models import PlannedBlock
from planner.models import PlannedWorkout


def build() -> PlannedWorkout:

    return PlannedWorkout(

        name="Tempo Ride",

        sport="cycling",

        target_tss=70,

        estimated_duration=90,

        blocks=[

            PlannedBlock(

                name="Warmup",

                duration=15 * 60,

                power_from=0.50,

                power_to=0.70,

                cadence_from=85,

                cadence_to=95,

            ),

            PlannedBlock(

                name="Tempo",

                duration=60 * 60,

                power_from=0.80,

                power_to=0.88,

                cadence_from=90,

                cadence_to=100,

            ),

            PlannedBlock(

                name="Cooldown",

                duration=15 * 60,

                power_from=0.45,

                power_to=0.60,

                cadence_from=80,

                cadence_to=90,

            ),

        ],

    )