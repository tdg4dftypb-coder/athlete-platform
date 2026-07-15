from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TrainingSession:

    start: datetime

    end: datetime

    workout_name: Optional[str]

    duration: int

    distance: Optional[float]

    energy: Optional[int]

    avg_power: Optional[int]

    normalized_power: Optional[int]

    max_power: Optional[int]

    avg_hr: Optional[int]

    max_hr: Optional[int]

    avg_cadence: Optional[int]

    max_cadence: Optional[int]

    tss: Optional[float]

    intensity_factor: Optional[float]

    ftp: Optional[int]