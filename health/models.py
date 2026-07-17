from dataclasses import dataclass

from engines.trend_engine import TrendMetric


@dataclass
class HealthState:

    weight: TrendMetric

    hrv: TrendMetric

    resting_hr: TrendMetric

    sleep: TrendMetric

    steps: TrendMetric