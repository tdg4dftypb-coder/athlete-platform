from performance.models import PerformanceState
from performance.training_load import TrainingLoad

from training.history.workout_history_builder import (
    WorkoutHistoryBuilder,
)


class PerformanceEngine:

    ATL_DAYS = 7
    CTL_DAYS = 42

    def __init__(self):

        self.history = WorkoutHistoryBuilder()

    def _build_load(self, period):

        average_daily = (
            period.total_tss / period.period_days
            if period.period_days
            else 0
        )

        average_workout = (
            period.total_tss / period.count
            if period.count
            else 0
        )

        return TrainingLoad(

            total_tss=period.total_tss,

            average_tss=average_workout,

            workouts=period.count,

            average_daily_tss=average_daily,

            period_days=period.period_days,

        )

    def analyze(self) -> PerformanceState:

        weekly = self.history.last_days(self.ATL_DAYS)

        monthly = self.history.last_days(self.CTL_DAYS)

        weekly_load = self._build_load(weekly)

        monthly_load = self._build_load(monthly)

        atl = weekly_load.average_daily_tss

        ctl = monthly_load.average_daily_tss

        tsb = ctl - atl

        return PerformanceState(

            weekly=weekly_load,

            monthly=monthly_load,

            atl=atl,

            ctl=ctl,

            tsb=tsb,

            fatigue=atl,

            fitness=ctl,

            freshness=tsb,

        )