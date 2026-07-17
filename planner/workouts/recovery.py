from planner.models import PlannedBlock
from planner.models import PlannedWorkout


def build() -> PlannedWorkout:

    return PlannedWorkout(

        name="Recovery Ride",

        sport="cycling",

        target_tss=25,

        estimated_duration=45,

        blocks=[

            PlannedBlock(

                name="Recovery",

                duration=45 * 60,

                power_from=0.45,

                power_to=0.55,

                cadence_from=85,

                cadence_to=95,

            )

        ],

    )