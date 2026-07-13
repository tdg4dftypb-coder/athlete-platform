from dataclasses import dataclass
from typing import Optional

from core.models import (
    HealthDaily,
    TrainingDaily,
    BodyComposition,
    BloodTest,
    BloodDonation,
)

from engines.trend_engine import TrendMetric


@dataclass
class HealthContext:
    """
    Dane potrzebne analizatorom.
    """

    today: HealthDaily

    hrv: TrendMetric
    resting_hr: TrendMetric
    sleep: TrendMetric

    training: Optional[TrainingDaily] = None

    body: Optional[BodyComposition] = None

    blood: Optional[BloodTest] = None

    donation: Optional[BloodDonation] = None