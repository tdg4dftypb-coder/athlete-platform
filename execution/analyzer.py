from execution.models import WorkoutExecution
from execution.scoring import ExecutionScoring

from training.analysis.workout_summary import WorkoutSummary
from workout.models import Workout


class ExecutionAnalyzer:

    def analyze(
        self,
        workout: Workout,
        summary: WorkoutSummary,
    ) -> WorkoutExecution:

        scoring = ExecutionScoring()

        power = scoring.power_score(
            workout,
            summary,
        )

        cadence = scoring.cadence_score(
            summary,
        )

        hr = scoring.hr_score(
            summary,
        )

        completion = scoring.completion(
            workout,
            summary,
        )

        execution = (

            power * 0.50 +

            cadence * 0.20 +

            hr * 0.10 +

            completion * 0.20

        )

        if execution >= 95:

            comment = "Excellent execution."

        elif execution >= 90:

            comment = "Very good execution."

        elif execution >= 80:

            comment = "Good execution."

        elif execution >= 70:

            comment = "Workout completed with noticeable deviations."

        else:

            comment = "Workout should be repeated."

        return WorkoutExecution(

            execution_score=round(execution, 1),

            power_score=round(power, 1),

            cadence_score=round(cadence, 1),

            hr_score=round(hr, 1),

            completion=round(completion, 1),

            comment=comment,
        )