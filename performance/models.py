from dataclasses import dataclass

from performance.training_load import TrainingLoad


@dataclass
class PerformanceState:

    weekly: TrainingLoad

    monthly: TrainingLoad

    atl: float

    ctl: float

    tsb: float