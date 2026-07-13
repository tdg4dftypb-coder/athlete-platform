from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TrendMetric:
    """
    Uniwersalny model trendu.

    Każda metryka (HRV, RHR, sen, masa itd.)
    będzie reprezentowana dokładnie tak samo.
    """

    today: Optional[float]

    average_7: Optional[float]
    average_30: Optional[float]

    delta: Optional[float]
    delta_percent: Optional[float]


class TrendEngine:

    @staticmethod
    def average(values: List[float]) -> Optional[float]:
        if not values:
            return None

        return sum(values) / len(values)

    @staticmethod
    def build(today: float,
              last_7: List[float],
              last_30: List[float]) -> TrendMetric:

        avg7 = TrendEngine.average(last_7)
        avg30 = TrendEngine.average(last_30)

        if avg7 is None:
            delta = None
            delta_percent = None
        else:
            delta = today - avg7

            if avg7 == 0:
                delta_percent = None
            else:
                delta_percent = (delta / avg7) * 100

        return TrendMetric(
            today=today,
            average_7=avg7,
            average_30=avg30,
            delta=delta,
            delta_percent=delta_percent,
        )