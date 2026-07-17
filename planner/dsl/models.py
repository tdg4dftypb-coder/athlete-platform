from dataclasses import dataclass


class Node:
    pass


@dataclass
class Workout(Node):

    name: str

    children: list[Node]


@dataclass
class Interval(Node):

    name: str

    duration: int

    power_from: float

    power_to: float

    cadence_from: int

    cadence_to: int


@dataclass
class Repeat(Node):

    count: int

    children: list[Node]