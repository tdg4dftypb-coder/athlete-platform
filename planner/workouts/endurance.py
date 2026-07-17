from planner.models import PlannedBlock
from planner.models import PlannedWorkout


def build() -> PlannedWorkout:

    return PlannedWorkout(

        name="Endurance Ride",

        sport="cycling",

        target_tss=55,

        estimated_duration=90,

        blocks=[

            PlannedBlock(

                name="Endurance",

                duration=90 * 60,

                power_from=0.60,

                power_to=0.75,

                cadence_from=85,

                cadence_to=95,

            )

        ],

    )