from dataclasses import dataclass

from training.analysis.workout_summary import WorkoutSummary


@dataclass
class WorkoutHistory:

    workouts: list[WorkoutSummary]

    @property
    def count(self):

        return len(self.workouts)

    @property
    def total_duration(self):

        return sum(

            w.duration

            for w in self.workouts

        )

    @property
    def total_distance(self):

        return sum(

            w.distance

            for w in self.workouts

        )

    @property
    def total_calories(self):

        return sum(

            w.calories

            for w in self.workouts

        )

    @property
    def total_tss(self):

        return sum(

            getattr(w, "tss", 0) or 0

            for w in self.workouts

        )

    @property
    def average_np(self):

        if not self.workouts:

            return 0

        return (

            sum(

                w.normalized_power

                for w in self.workouts

            )

            / len(self.workouts)

        )

    @property
    def average_power(self):

        if not self.workouts:

            return 0

        return (

            sum(

                w.average_power

                for w in self.workouts

            )

            / len(self.workouts)

        )