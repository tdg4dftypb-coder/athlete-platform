from dataclasses import dataclass

from planner.catalog.stimulus import StressLevel


@dataclass(frozen=True, slots=True)
class AnalyticsProfile:

    aerobic_load: StressLevel

    muscular_load: StressLevel

    metabolic_load: StressLevel

    neurological_load: StressLevel

    fatigue_index: float