from statistics import mean
from typing import List, Optional

from core.context import HealthContext
from core.models import HealthDaily


class TrendEngine:
    """
    Odpowiada za wyliczanie trendów z danych historycznych.
    Nie podejmuje decyzji — tylko przygotowuje dane
    dla analizatorów.
    """

    def build_context(
        self,
        today: HealthDaily,
        history: List[HealthDaily],
    ) -> HealthContext:

        context = HealthContext(
            today=today,
            history=history,
        )

        context.hrv_avg_7 = self._average(history, "hrv", 7)
        context.resting_hr_avg_7 = self._average(history, "resting_hr", 7)

        return context

    def _average(
        self,
        history: List[HealthDaily],
        field: str,
        days: int,
    ) -> Optional[float]:

        values = []

        for day in history[-days:]:

            value = getattr(day, field)

            if value is not None:
                values.append(value)

        if not values:
            return None

        return round(mean(values), 1)