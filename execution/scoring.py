from training.analysis.workout_summary import WorkoutSummary
from workout.models import Workout


class ExecutionScoring:

    def power_score(
        self,
        workout: Workout,
        summary: WorkoutSummary,
    ) -> float:

        if workout.target_if == 0:

            return 100

        ratio = summary.intensity_factor / workout.target_if

        score = 100 - abs(1 - ratio) * 100

        return max(0, min(100, score))

    def cadence_score(
        self,
        summary: WorkoutSummary,
    ) -> float:

        cadence = summary.average_cadence

        if cadence >= 90:

            return 100

        if cadence >= 85:

            return 95

        if cadence >= 80:

            return 90

        if cadence >= 75:

            return 80

        return 70

    def hr_score(
        self,
        summary: WorkoutSummary,
    ) -> float:

        hr = summary.average_hr

        if hr >= 150:

            return 100

        if hr >= 140:

            return 95

        if hr >= 130:

            return 90

        if hr >= 120:

            return 85

        return 80

    def completion(
        self,
        workout: Workout,
        summary: WorkoutSummary,
    ) -> float:

        if workout.duration == 0:

            return 100

        ratio = summary.duration / (workout.duration * 60)

        ratio = min(1.0, ratio)

        return ratio * 100