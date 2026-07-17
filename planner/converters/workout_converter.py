from planner.models import PlannedWorkout

from workout.models import (
    Workout,
    WorkoutBlock,
)


class WorkoutConverter:

    def convert(
        self,
        planned: PlannedWorkout,
    ) -> Workout:

        blocks = []

        for block in planned.blocks:

            blocks.append(

                WorkoutBlock(

                    name=block.name,

                    duration=block.duration,

                    power_from=block.power_from,

                    power_to=block.power_to,

                    cadence_from=block.cadence_from,

                    cadence_to=block.cadence_to,

                    repeat=block.repeat,

                    description="",

                )

            )

        return Workout(

            name=planned.name,

            sport=planned.sport,

            blocks=blocks,

        )