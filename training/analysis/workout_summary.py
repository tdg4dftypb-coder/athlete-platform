from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
    # Advanced Metrics
    #

    efficiency_factor: Optional[float] = None

    variability_index: Optional[float] = None

    hr_drift: Optional[float] = None

    aerobic_decoupling: Optional[float] = None

    training_load_ratio: Optional[float] = None

    average_speed: Optional[float] = None

    average_pace: Optional[float] = None

    elevation_gain: Optional[float] = None

    elevation_loss: Optional[float] = None

    #
    # Zones
    #

    zones: PowerZones = None