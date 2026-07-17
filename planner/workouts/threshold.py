from planner.models import PlannedWorkout


def build() -> PlannedWorkout:

    return PlannedWorkout(

        name="Threshold Ride",

        sport="cycling",

        target_tss=90,

        estimated_duration=75,

        blocks=[],

    )