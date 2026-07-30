from athlete.models import AthleteState

from health.models import HealthState

from core.context import HealthContext

from performance.models import PerformanceState

from recovery.models import RecoveryResult

from training.analysis.workout_summary import WorkoutSummary


class AthleteStateBuilder:

    def build(
        self,
        health: HealthState,
        context: HealthContext,
        recovery: RecoveryResult,
        performance: PerformanceState,
        workout: WorkoutSummary = None,
    ) -> AthleteState:

        return AthleteState(
            health=health,
            context=context,
            recovery=recovery,
            performance=performance,
            last_workout=workout,
        )
    