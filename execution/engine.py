from execution.models import ExecutionState

from workout.models import Workout

from training.analysis.workout_summary import WorkoutSummary


class ExecutionEngine:

    @staticmethod
    def _score(
        planned: float,
        actual: float,
    ) -> float:

        if planned <= 0:
            return 100.0

        ratio = actual / planned

        score = ratio * 100

        if score > 100:
            score = 100

        return round(score, 1)

    def analyze(
        self,
        workout: Workout,
        activity: WorkoutSummary,
    ) -> ExecutionState:

        duration_score = self._score(

            workout.duration,

            activity.duration / 60,

        )

        tss_score = self._score(

            workout.target_tss,

            activity.tss,

        )

        overall = round(

            (duration_score + tss_score) / 2,

            1,

        )

        completed = overall >= 90

        reasons = []

        if duration_score < 90:

            reasons.append(

                "Workout shorter than planned"

            )

        if tss_score < 90:

            reasons.append(

                "Training load below target"

            )

        if completed:

            reasons.append(

                "Workout completed"

            )

        return ExecutionState(

            planned_duration=workout.duration,

            executed_duration=round(

                activity.duration / 60

            ),

            duration_score=duration_score,

            planned_tss=workout.target_tss,

            executed_tss=activity.tss,

            tss_score=tss_score,

            overall_score=overall,

            completed=completed,

            reasons=reasons,

        )