from dataclasses import dataclass

from athlete.memory.models import AthleteMemoryEvent
from athlete.memory.writer import AthleteMemoryWriter
from pipeline.models import PostWorkoutResult
from pipeline.post_workout import PostWorkoutPipeline
from training.activity import Activity
from workout.models import Workout


@dataclass(frozen=True)
class PostWorkoutRecordingResult:
    post_workout: PostWorkoutResult
    event: AthleteMemoryEvent


class PostWorkoutRecordingService:
    """Records the analysed result of a completed workout in Athlete Memory."""

    def __init__(
        self,
        pipeline: PostWorkoutPipeline,
        writer: AthleteMemoryWriter,
    ) -> None:

        self.pipeline = pipeline
        self.writer = writer

    def record(
        self,
        workout: Workout,
        activity: Activity,
    ) -> PostWorkoutRecordingResult:

        post_workout = self.pipeline.run(workout, activity)
        event = self.writer.write(post_workout)

        return PostWorkoutRecordingResult(
            post_workout=post_workout,
            event=event,
        )
