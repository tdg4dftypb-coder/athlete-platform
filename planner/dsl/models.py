from dataclasses import dataclass


class Node:
    pass


@dataclass
class WorkoutPrescription:

    duration: int

    target_tss: float = 0

    intensity: float = 1.0


@dataclass
class Workout(Node):

    name: str

    children: list[Node]

    prescription: WorkoutPrescription | None = None

    @property
    def target_tss(
        self,
    ) -> float:

        if self.prescription is None:
            return 0

        return self.prescription.target_tss


@dataclass
class Interval(Node):

    name: str

    duration: int

    power_from: float

    power_to: float

    cadence_from: int

    cadence_to: int

    intensity: float = 1.0


@dataclass
class Repeat(Node):

    count: int

    children: list[Node]