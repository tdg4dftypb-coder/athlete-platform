from dataclasses import dataclass
from datetime import datetime

from training.calculations.power_zones import PowerZones


@dataclass
class WorkoutSummary:

    #
    # Session
    #

    start: datetime

    end: datetime

    sport: str

    #
    # Basic
    #

    duration: int

    distance: float

    calories: int

    #
    # Power
    #

    average_power: float

    normalized_power: float

    max_power: int

    intensity_factor: float

    tss: float

    #
    # Heart Rate
    #

    average_hr: float

    max_hr: int

    #
    # Cadence
    #

    average_cadence: float

    max_cadence: int

    #
    # Zones
    #

    zones: PowerZones