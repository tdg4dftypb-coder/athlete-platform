from core.context import HealthContext
from core.models import HealthDaily
from engines.trend_engine import TrendEngine


class ContextBuilder:
    """
    Buduje kompletny HealthContext
    z historii pomiarów.
    """

    def build(self, history: list[HealthDaily]) -> HealthContext:

        today = history[-1]

        hrv_values = [
            x.hrv
            for x in history
            if x.hrv is not None
        ]

        rhr_values = [
            x.resting_hr
            for x in history
            if x.resting_hr is not None
        ]

        sleep_values = [
            x.sleep_duration
            for x in history
            if x.sleep_duration is not None
        ]

        hrv = TrendEngine.build(
            today=today.hrv,
            last_7=hrv_values[-7:],
            last_30=hrv_values[-30:]
        )

        resting_hr = TrendEngine.build(
            today=today.resting_hr,
            last_7=rhr_values[-7:],
            last_30=rhr_values[-30:]
        )

        sleep = TrendEngine.build(
            today=today.sleep_duration,
            last_7=sleep_values[-7:],
            last_30=sleep_values[-30:]
        )

        return HealthContext(
            today=today,
            hrv=hrv,
            resting_hr=resting_hr,
            sleep=sleep,
        )