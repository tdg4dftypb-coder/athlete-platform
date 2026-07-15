from timeline.models import TimelineBlock
from timeline.models import WorkoutTimeline

from workout.models import Workout


class TimelineBuilder:

    def build(
        self,
        workout: Workout,
    ) -> WorkoutTimeline:

        blocks = []

        current = 0

        for index, block in enumerate(workout.blocks, start=1):

            for repeat in range(block.repeat):

                start = current

                end = current + block.duration

                blocks.append(

                    TimelineBlock(

                        index=index,

                        name=block.name,

                        start=start,

                        end=end,

                        duration=block.duration,

                        power_from=block.power_from,

                        power_to=block.power_to,

                        cadence_from=block.cadence_from,

                        cadence_to=block.cadence_to,

                        repeat=repeat + 1,

                        description=block.description,

                    )

                )

                current = end

        return WorkoutTimeline(

            blocks=blocks,

            total_duration=current,

        )