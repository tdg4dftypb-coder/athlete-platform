from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class SleepSession:

    sleep_date: date

    start: datetime

    end: datetime

    duration: int

    in_bed: int

    awake: int

    rem: int

    core: int

    deep: int

    efficiency: Optional[float]