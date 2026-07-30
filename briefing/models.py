from dataclasses import dataclass

from decision.models import DecisionResult
from performance.models import PerformanceState
from recovery.models import RecoveryResult
from training.analysis.workout_summary import WorkoutSummary


@dataclass
class MorningBriefing:

    recovery: RecoveryResult

    performance: PerformanceState

    today: DecisionResult

    last_workout: WorkoutSummary | None