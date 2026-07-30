from athlete.memory.models import AthleteMemorySnapshot, TrainingTrendReport


class TrendEngine:
    """Calculates basic deterministic training trends from a memory snapshot."""

    def analyze(
        self,
        snapshot: AthleteMemorySnapshot,
    ) -> TrainingTrendReport:

        observations = snapshot.workout_observations
        workouts_count = len(observations)

        return TrainingTrendReport(
            period=snapshot.period,
            workouts_count=workouts_count,
            planned_duration=sum(
                observation.planned_duration
                for observation in observations
            ),
            executed_duration=sum(
                observation.executed_duration
                for observation in observations
            ),
            planned_tss=sum(
                observation.planned_tss
                for observation in observations
            ),
            executed_tss=sum(
                observation.executed_tss
                for observation in observations
            ),
            average_completion_score=(
                sum(
                    observation.completion_score
                    for observation in observations
                )
                / workouts_count
                if workouts_count
                else 0.0
            ),
            average_execution_score=(
                sum(
                    observation.execution_score
                    for observation in observations
                )
                / workouts_count
                if workouts_count
                else 0.0
            ),
        )
