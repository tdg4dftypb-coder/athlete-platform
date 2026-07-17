from athlete.models import AthleteState
from athlete.state_builder import AthleteStateBuilder

from core.context import HealthContext

from performance.models import PerformanceState
from recovery.models import RecoveryResult
from training.analysis.workout_summary import WorkoutSummary


class AthleteEngine:

    def __init__(self):

        self.builder = AthleteStateBuilder()

    def build(

        self,

        health: HealthContext,

        recovery: RecoveryResult,

        performance: PerformanceState,

        workout: WorkoutSummary = None,

    ) -> AthleteState:

        return self.builder.build(

            health=health,

            recovery=recovery,

            performance=performance,

            workout=workout,

        )