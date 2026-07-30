from planner.dsl.workouts.endurance import build as endurance
from planner.dsl.workouts.recovery import build as recovery
from planner.dsl.workouts.threshold import build as threshold
from planner.dsl.workouts.vo2 import build as vo2

__all__ = [
    "recovery",
    "endurance",
    "threshold",
    "vo2",
]