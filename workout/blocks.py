from dataclasses import dataclass


@dataclass
class WorkoutBlock:

    #
    # Identity
    #

    name: str

    description: str

    #
    # Duration
    #

    duration: int

    #
    # Power (% FTP)
    #

    power_from: float

    power_to: float

    #
    # Cadence
    #

    cadence_from: int

    cadence_to: int

    #
    # Structure
    #

    repeat: int = 1


@dataclass
class WarmupBlock(WorkoutBlock):
    pass


@dataclass
class EnduranceBlock(WorkoutBlock):
    pass


@dataclass
class TempoBlock(WorkoutBlock):
    pass


@dataclass
class ThresholdBlock(WorkoutBlock):
    pass


@dataclass
class VO2Block(WorkoutBlock):
    pass


@dataclass
class SprintBlock(WorkoutBlock):
    pass


@dataclass
class RecoveryBlock(WorkoutBlock):
    pass


@dataclass
class CooldownBlock(WorkoutBlock):
    pass