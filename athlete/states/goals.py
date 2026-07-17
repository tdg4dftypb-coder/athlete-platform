from dataclasses import dataclass


@dataclass
class GoalState:

    primary_goal: str = ""

    secondary_goal: str = ""