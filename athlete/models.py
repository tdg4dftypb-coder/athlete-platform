from dataclasses import dataclass
from typing import Optional

from health.models import HealthState

from core.context import HealthContext

from performance.models import PerformanceState

from recovery.models import RecoveryResult

from decision.models import DecisionState

from training.analysis.workout_summary import WorkoutSummary


@dataclass
class AthleteState:

    #
    # Long-term
    #

    health: HealthState

    #
    # Daily
    #

    context: HealthContext

    recovery: RecoveryResult

    performance: PerformanceState

    decision: Optional[DecisionState] = None

    last_workout: Optional[WorkoutSummary] = None