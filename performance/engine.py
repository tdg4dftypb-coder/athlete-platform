from performance.models import PerformanceState
from performance.training_load import TrainingLoad

from training.history.workout_history_builder import (
    WorkoutHistoryBuilder,
)


class PerformanceEngine:

    def __init__(self):

        self.history = WorkoutHistoryBuilder()

    def analyze(self) -> PerformanceState:

        weekly = self.history.last_days(7)

        monthly = self.history.last_days(42)

        weekly_load = TrainingLoad(

            total_tss=weekly.total_tss,

            average_tss=(
                weekly.total_tss / weekly.count
                if weekly.count
                else 0
            ),

            workouts=weekly.count,

        )

        monthly_load = TrainingLoad(

            total_tss=monthly.total_tss,

            average_tss=(
                monthly.total_tss / monthly.count
                if monthly.count
                else 0
            ),

            workouts=monthly.count,

        )

        atl = weekly_load.average_tss

        ctl = monthly_load.average_tss

        tsb = ctl - atl

        return PerformanceState(

            weekly=weekly_load,

            monthly=monthly_load,

            atl=atl,

            ctl=ctl,

            tsb=tsb,

        )