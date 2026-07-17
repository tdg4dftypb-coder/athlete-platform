from dataclasses import dataclass

from performance.models import PerformanceState


@dataclass
class PerformanceStateModel:

    state: PerformanceState