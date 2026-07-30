from dataclasses import dataclass

from execution.result import ExecutionResult
from feedback.models import WorkoutFeedback
from training.activity import Activity
from training.analysis.workout_summary import WorkoutSummary
from workout.models import Workout


@dataclass(frozen=True)
class PostWorkoutResult:
    workout: Workout
    activity: Activity
    workout_summary: WorkoutSummary
    execution: ExecutionResult
    feedback: WorkoutFeedback
