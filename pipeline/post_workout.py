from execution.context import ExecutionContext
from execution.engine import ExecutionEngine
from feedback.engine import WorkoutFeedbackEngine
from pipeline.models import PostWorkoutResult
from timeline.builder import TimelineBuilder
from training.activity import Activity
from training.analysis.workout_analyzer import WorkoutAnalyzer
from workout.models import Workout


class PostWorkoutPipeline:

    def __init__(
        self,
        workout_analyzer: WorkoutAnalyzer | None = None,
        timeline_builder: TimelineBuilder | None = None,
        execution_engine: ExecutionEngine | None = None,
        feedback_engine: WorkoutFeedbackEngine | None = None,
    ) -> None:

        self.workout_analyzer = workout_analyzer or WorkoutAnalyzer()
        self.timeline_builder = timeline_builder or TimelineBuilder()
        self.execution_engine = execution_engine or ExecutionEngine()
        self.feedback_engine = feedback_engine or WorkoutFeedbackEngine()

    def run(
        self,
        workout: Workout,
        activity: Activity,
    ) -> PostWorkoutResult:

        summary = self.workout_analyzer.analyze(activity)
        timeline = self.timeline_builder.build(workout)

        execution = self.execution_engine.analyze_context(
            ExecutionContext(
                workout=workout,
                activity=activity,
                summary=summary,
                timeline=timeline,
            )
        )

        feedback = self.feedback_engine.build(execution)

        return PostWorkoutResult(
            workout=workout,
            activity=activity,
            workout_summary=summary,
            execution=execution,
            feedback=feedback,
        )
