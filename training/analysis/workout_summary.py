from dataclasses import dataclass

from training.calculations.power_zones import PowerZones


@dataclass
class WorkoutSummary:

    duration: int

    distance: float

    calories: int

    average_power: float

    normalized_power: float

    intensity_factor: float

    tss: float

    max_power: int

    average_hr: float

    max_hr: int

    average_cadence: float

    max_cadence: int

    zones: PowerZones