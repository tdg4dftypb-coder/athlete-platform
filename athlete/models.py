from dataclasses import dataclass
from typing import Optional

from core.context import HealthContext

from performance.models import PerformanceState

from recovery.models import RecoveryResult

from training.analysis.workout_summary import WorkoutSummary


@dataclass
class AthleteState:

    health: HealthContext

    recovery: RecoveryResult

    performance: PerformanceState

    last_workout: Optional[WorkoutSummary]