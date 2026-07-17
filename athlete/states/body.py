from dataclasses import dataclass

from typing import Optional

from core.models import BodyComposition


@dataclass
class BodyState:

    composition: Optional[BodyComposition] = None