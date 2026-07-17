from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class AthleteEvent:

    timestamp: datetime

    category: str

    title: str

    payload: Any = None