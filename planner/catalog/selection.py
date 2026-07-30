from dataclasses import dataclass
from enum import Enum


class TrainingPhase(Enum):

    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class SelectionProfile:

    #
    # Availability
    #

    min_duration: int

    max_duration: int

    #
    # Recovery constraints
    #

    min_recovery_score: int = 0

    max_fatigue_score: int = 100

    #
    # Planning
    #

    phases: tuple[TrainingPhase, ...] = ()

    progression_level: int = 1