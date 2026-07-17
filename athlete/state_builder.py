from athlete.models import AthleteState

from health.models import HealthState

from core.context import HealthContext

from performance.models import PerformanceState

from recovery.models import RecoveryResult

from decision.models import DecisionState

from training.analysis.workout_summary import WorkoutSummary


class AthleteStateBuilder:

    def build(

        self,

        health: HealthState,

        context: HealthContext,

        recovery: RecoveryResult,

        performance: PerformanceState,

        decision: DecisionState = None,

        workout: WorkoutSummary = None,

    ) -> AthleteState:

        return AthleteState(

            health=health,

            context=context,

            recovery=recovery,

            performance=performance,

            decision=decision,

            last_workout=workout,

        )