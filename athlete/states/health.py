from dataclasses import dataclass

from core.context import HealthContext


@dataclass
class HealthState:

    context: HealthContext