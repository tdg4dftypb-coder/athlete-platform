from athlete.history.event import AthleteEvent

from training.analysis.workout_summary import WorkoutSummary


class WorkoutEventFactory:

    @staticmethod
    def build(

        workouts: list[WorkoutSummary],

    ) -> list[AthleteEvent]:

        events = []

        for workout in workouts:

            events.append(

                AthleteEvent(

                    timestamp=workout.start,

                    category="WORKOUT",

                    title=workout.sport,

                    payload=workout,

                )

            )

        return events