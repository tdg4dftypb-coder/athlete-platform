from datetime import date

from analyzers.readiness.analyzer import ReadinessAnalyzer
from core.context import HealthContext
from core.models import HealthDaily
from engines.trend_engine import TrendMetric


def build_context(
    hrv_today,
    hrv_avg,
    rhr_today,
    rhr_avg,
    sleep_minutes,
):

    return HealthContext(

        today=HealthDaily(
            date=date.today(),
            hrv=hrv_today,
            resting_hr=rhr_today,
            sleep_duration=sleep_minutes,
        ),

        hrv=TrendMetric(
            today=hrv_today,
            average_7=hrv_avg,
            average_30=hrv_avg,
            delta=hrv_today - hrv_avg,
            delta_percent=((hrv_today - hrv_avg) / hrv_avg) * 100,
        ),

        resting_hr=TrendMetric(
            today=rhr_today,
            average_7=rhr_avg,
            average_30=rhr_avg,
            delta=rhr_today - rhr_avg,
            delta_percent=((rhr_today - rhr_avg) / rhr_avg) * 100,
        ),

        sleep=TrendMetric(
            today=sleep_minutes,
            average_7=sleep_minutes,
            average_30=sleep_minutes,
            delta=0,
            delta_percent=0,
        ),
    )


def test_green_day():

    context = build_context(
        hrv_today=70,
        hrv_avg=70,
        rhr_today=45,
        rhr_avg=45,
        sleep_minutes=480,
    )

    result = ReadinessAnalyzer().analyze(context)

    assert result.status == "🟢 GOTOWY"


def test_yellow_day():

    context = build_context(
        hrv_today=65,
        hrv_avg=70,
        rhr_today=49,
        rhr_avg=46,
        sleep_minutes=400,
    )

    result = ReadinessAnalyzer().analyze(context)

    assert result.status == "🟡 OSTROŻNIE"


def test_red_day():

    context = build_context(
        hrv_today=55,
        hrv_avg=70,
        rhr_today=55,
        rhr_avg=46,
        sleep_minutes=300,
    )

    result = ReadinessAnalyzer().analyze(context)

    assert result.status == "🔴 ODPUŚĆ"