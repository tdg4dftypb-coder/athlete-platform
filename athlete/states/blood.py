from dataclasses import dataclass

from typing import Optional

from core.models import BloodTest


@dataclass
class BloodState:

    latest: Optional[BloodTest] = None