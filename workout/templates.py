from dataclasses import dataclass


@dataclass
class WorkoutTemplate:

    name: str

    goal: str

    description: str

    duration: int

    target_if: float

    target_tss: float


@dataclass
class RecoveryTemplate(WorkoutTemplate):

    pass


@dataclass
class EnduranceTemplate(WorkoutTemplate):

    pass


@dataclass
class TempoTemplate(WorkoutTemplate):

    pass


@dataclass
class ThresholdTemplate(WorkoutTemplate):

    pass


@dataclass
class VO2Template(WorkoutTemplate):

    pass


@dataclass
class SprintTemplate(WorkoutTemplate):

    pass