from dataclasses import dataclass

from training.activity import Activity
from training.analysis.workout_summary import WorkoutSummary
from timeline.models import WorkoutTimeline
from workout.models import Workout


@dataclass(frozen=True)
class ExecutionContext:

    workout: Workout

    activity: Activity

    summary: WorkoutSummary

    timeline: WorkoutTimeline