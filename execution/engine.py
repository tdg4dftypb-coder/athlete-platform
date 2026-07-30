from execution.context import ExecutionContext
from execution.block_analyzer import BlockAnalyzer
from execution.result import ExecutionResult

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
    ) -> ExecutionResult:

        return self._build_result(
            workout,
            activity,
            [],
        )


    def analyze_context(
        self,
        context: ExecutionContext,
    ) -> ExecutionResult:

        blocks = []

        analyzer = BlockAnalyzer()

        for block in context.timeline.blocks:

            blocks.append(

                analyzer.analyze(

                    block,

                    context.activity,

                )

            )


        return self._build_result(

            context.workout,

            context.summary,

            blocks,

        )


    def _build_result(
        self,
        workout: Workout,
        activity: WorkoutSummary,
        blocks,
    ) -> ExecutionResult:

        completion_score = self._score(

            workout.duration,

            activity.duration / 60,

        )

        load_score = self._score(

            workout.target_tss,

            activity.tss,

        )

        execution_score = round(

            (
                completion_score
                +
                load_score
            )
            / 2,

            1,

        )

        completed = execution_score >= 90


        insights = []


        if completion_score < 90:

            insights.append(
                "Workout shorter than planned",
            )


        if load_score < 90:

            insights.append(
                "Training load below target",
            )


        if completed:

            insights.append(
                "Workout completed",
            )


        return ExecutionResult(

            planned_duration=workout.duration,

            executed_duration=round(
                activity.duration / 60,
            ),

            planned_tss=workout.target_tss,

            executed_tss=activity.tss,

            completion_score=completion_score,

            power_score=None,

            cadence_score=None,

            heart_rate_score=None,

            execution_score=execution_score,

            completed=completed,

            blocks=blocks,

            insights=insights,

        )