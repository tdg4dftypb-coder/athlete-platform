from dataclasses import dataclass

from coach.models import CoachRecommendation
from decision.models import DecisionState
from performance.models import PerformanceState


@dataclass
class MorningBriefing:

    #
    # Date
    #

    date: str

    #
    # Recovery
    #

    recovery_score: int

    recovery_status: str

    #
    # Performance
    #

    performance: PerformanceState

    #
    # Decision
    #

    decision: DecisionState

    #
    # Coach
    #

    recommendation: CoachRecommendation

    #
    # Health
    #

    hrv: int

    resting_hr: int

    sleep_minutes: int

    steps: int

    #
    # Last workout
    #

    workout_duration: int

    workout_avg_power: int

    workout_np: int

    workout_avg_hr: int