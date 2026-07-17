from planner.models import PlannedWorkout


def build() -> PlannedWorkout:

    return PlannedWorkout(

        name="VO2 Ride",

        sport="cycling",

        target_tss=100,

        estimated_duration=75,

        blocks=[],

    )