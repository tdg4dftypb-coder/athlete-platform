from dataclasses import dataclass


@dataclass
class CalendarState:

    next_workout: str = ""

    next_race: str = ""