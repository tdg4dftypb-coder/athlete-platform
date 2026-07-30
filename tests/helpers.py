from datetime import date

from athlete.models import AthleteState

from core.context import HealthContext
from core.models import HealthDaily

from engines.trend_engine import TrendMetric

from health.models import HealthState

from performance.models import PerformanceState
from performance.training_load import TrainingLoad

from recovery.models import (
    RecoveryMetric,
    RecoveryResult,
)


def build_trend(
    today: float,
    average: float,
) -> TrendMetric:

    delta = today - average

    return TrendMetric(
        today=today,
        average_7=average,
        average_30=average,
        delta=delta,
        delta_percent=(delta / average) * 100 if average else 0,
    )


def build_context(
    hrv: float = 70,
    resting_hr: float = 45,
    sleep: int = 480,
) -> HealthContext:

    return HealthContext(
        today=HealthDaily(
            date=date.today(),
            hrv=hrv,
            resting_hr=resting_hr,
            sleep_duration=sleep,
        ),
        hrv=build_trend(hrv, hrv),
        resting_hr=build_trend(resting_hr, resting_hr),
        sleep=build_trend(sleep, sleep),
    )


def build_health() -> HealthState:

    trend = build_trend(1, 1)

    return HealthState(
        weight=trend,
        hrv=trend,
        resting_hr=trend,
        sleep=trend,
        steps=trend,
    )


def build_recovery(
    score: int = 80,
) -> RecoveryResult:

    metric = RecoveryMetric(
        value=0,
        baseline=0,
        delta=0,
        delta_percent=0,
        score=score,
    )

    return RecoveryResult(
        score=score,
        status="OK",
        reasons=[],
        hrv=metric,
        resting_hr=metric,
        sleep=metric,
    )


def build_training_load() -> TrainingLoad:

    return TrainingLoad(
        total_tss=0,
        average_tss=0,
        workouts=0,
        average_daily_tss=0,
        period_days=7,
    )


def build_performance(
    fatigue: float = 0,
    freshness: float = 0,
) -> PerformanceState:

    load = build_training_load()

    return PerformanceState(
        weekly=load,
        monthly=load,
        atl=0,
        ctl=0,
        tsb=0,
        fatigue=fatigue,
        fitness=0,
        freshness=freshness,
    )


def build_athlete(
    recovery_score: int = 80,
    fatigue: float = 0,
    freshness: float = 0,
) -> AthleteState:

    return AthleteState(
        health=build_health(),
        context=build_context(),
        recovery=build_recovery(recovery_score),
        performance=build_performance(
            fatigue=fatigue,
            freshness=freshness,
        ),
    )