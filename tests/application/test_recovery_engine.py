from datetime import date
import pytest

from core.context import HealthContext
from core.models import HealthDaily
from engines.trend_engine import TrendMetric
from recovery.engine import RecoveryEngine
from recovery.models import RecoveryMetricStatus


def build_health_context(
    hrv_today=70.0,
    hrv_avg=70.0,
    rhr_today=45.0,
    rhr_avg=45.0,
    sleep_minutes=480,
):
    hrv_delta = hrv_today - hrv_avg if (hrv_today is not None and hrv_avg is not None) else None
    hrv_delta_pct = ((hrv_today - hrv_avg) / hrv_avg * 100.0) if (hrv_today is not None and hrv_avg is not None and hrv_avg > 0) else None

    rhr_delta = rhr_today - rhr_avg if (rhr_today is not None and rhr_avg is not None) else None
    rhr_delta_pct = ((rhr_today - rhr_avg) / rhr_avg * 100.0) if (rhr_today is not None and rhr_avg is not None and rhr_avg > 0) else None

    sleep_avg = sleep_minutes if sleep_minutes is not None else None

    return HealthContext(
        today=HealthDaily(
            date=date(2026, 8, 7),
            hrv=hrv_today,
            resting_hr=rhr_today,
            sleep_duration=sleep_minutes,
        ),
        hrv=TrendMetric(
            today=hrv_today,
            average_7=hrv_avg,
            average_30=hrv_avg,
            delta=hrv_delta,
            delta_percent=hrv_delta_pct,
        ),
        resting_hr=TrendMetric(
            today=rhr_today,
            average_7=rhr_avg,
            average_30=rhr_avg,
            delta=rhr_delta,
            delta_percent=rhr_delta_pct,
        ),
        sleep=TrendMetric(
            today=sleep_minutes,
            average_7=sleep_avg,
            average_30=sleep_avg,
            delta=0,
            delta_percent=0,
        ),
    )


def test_hrv_metric_statuses_and_score_preservation():
    engine = RecoveryEngine()

    # 1. Limiting (delta_pct <= -15)
    ctx_lim = build_health_context(hrv_today=80, hrv_avg=100) # delta_pct = -20%
    res_lim = engine.analyze(ctx_lim)
    assert res_lim.hrv.status == RecoveryMetricStatus.LIMITING
    assert res_lim.hrv.score == 75

    # 2. Caution (-15 < delta_pct <= -5)
    ctx_caut = build_health_context(hrv_today=90, hrv_avg=100) # delta_pct = -10%
    res_caut = engine.analyze(ctx_caut)
    assert res_caut.hrv.status == RecoveryMetricStatus.CAUTION
    assert res_caut.hrv.score == 90

    # 3. Supportive (delta_pct >= 5)
    ctx_supp = build_health_context(hrv_today=110, hrv_avg=100) # delta_pct = +10%
    res_supp = engine.analyze(ctx_supp)
    assert res_supp.hrv.status == RecoveryMetricStatus.SUPPORTIVE
    assert res_supp.hrv.score == 100 # capped at 100

    # 4. Neutral (-5 < delta_pct < 5)
    ctx_neu = build_health_context(hrv_today=100, hrv_avg=100) # delta_pct = 0%
    res_neu = engine.analyze(ctx_neu)
    assert res_neu.hrv.status == RecoveryMetricStatus.NEUTRAL
    assert res_neu.hrv.score == 100

    # 5. Unavailable (no delta_percent)
    ctx_unavail = build_health_context(hrv_today=None, hrv_avg=100)
    res_unavail = engine.analyze(ctx_unavail)
    assert res_unavail.hrv.status == RecoveryMetricStatus.UNAVAILABLE


def test_rhr_metric_statuses_and_score_preservation():
    engine = RecoveryEngine()

    # 1. Limiting (delta >= 8)
    ctx_lim = build_health_context(rhr_today=58, rhr_avg=50) # delta = +8
    res_lim = engine.analyze(ctx_lim)
    assert res_lim.resting_hr.status == RecoveryMetricStatus.LIMITING
    assert res_lim.resting_hr.score == 80

    # 2. Caution (4 <= delta < 8)
    ctx_caut = build_health_context(rhr_today=55, rhr_avg=50) # delta = +5
    res_caut = engine.analyze(ctx_caut)
    assert res_caut.resting_hr.status == RecoveryMetricStatus.CAUTION
    assert res_caut.resting_hr.score == 90

    # 3. Supportive (delta <= -2)
    ctx_supp = build_health_context(rhr_today=47, rhr_avg=50) # delta = -3
    res_supp = engine.analyze(ctx_supp)
    assert res_supp.resting_hr.status == RecoveryMetricStatus.SUPPORTIVE
    assert res_supp.resting_hr.score == 100

    # 4. Neutral (-2 < delta < 4)
    ctx_neu = build_health_context(rhr_today=51, rhr_avg=50) # delta = +1
    res_neu = engine.analyze(ctx_neu)
    assert res_neu.resting_hr.status == RecoveryMetricStatus.NEUTRAL

    # 5. Unavailable (no RHR)
    ctx_unavail = build_health_context(rhr_today=None, rhr_avg=50)
    res_unavail = engine.analyze(ctx_unavail)
    assert res_unavail.resting_hr.status == RecoveryMetricStatus.UNAVAILABLE


def test_sleep_metric_statuses_and_score_preservation():
    engine = RecoveryEngine()

    # 1. Limiting (hours < 6)
    ctx_lim = build_health_context(sleep_minutes=300) # 5.0h
    res_lim = engine.analyze(ctx_lim)
    assert res_lim.sleep.status == RecoveryMetricStatus.LIMITING
    assert res_lim.sleep.score == 80

    # 2. Caution (6 <= hours < 7)
    ctx_caut = build_health_context(sleep_minutes=390) # 6.5h
    res_caut = engine.analyze(ctx_caut)
    assert res_caut.sleep.status == RecoveryMetricStatus.CAUTION
    assert res_caut.sleep.score == 90

    # 3. Supportive (hours >= 8)
    ctx_supp = build_health_context(sleep_minutes=510) # 8.5h
    res_supp = engine.analyze(ctx_supp)
    assert res_supp.sleep.status == RecoveryMetricStatus.SUPPORTIVE
    assert res_supp.sleep.score == 100

    # 4. Neutral (7 <= hours < 8)
    ctx_neu = build_health_context(sleep_minutes=450) # 7.5h
    res_neu = engine.analyze(ctx_neu)
    assert res_neu.sleep.status == RecoveryMetricStatus.NEUTRAL

    # 5. Unavailable (no sleep)
    ctx_unavail = build_health_context(sleep_minutes=None)
    res_unavail = engine.analyze(ctx_unavail)
    assert res_unavail.sleep.status == RecoveryMetricStatus.UNAVAILABLE
