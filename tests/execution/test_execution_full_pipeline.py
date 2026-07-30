from datetime import datetime, timedelta

from execution.context import ExecutionContext
from execution.engine import ExecutionEngine
from execution.result import ExecutionResult

from timeline.builder import TimelineBuilder

from training.activity import (
    Activity,
    ActivityRecord,
)

from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.blocks import WorkoutBlock
from workout.models import Workout


def test_full_execution_pipeline():

    workout = Workout(

        name="Threshold Test",

        goal="FTP development",

        description="",

        duration=5,

        target_tss=10,

        target_if=0.95,

        blocks=[

            WorkoutBlock(

                name="Threshold",

                duration=300,

                power_from=250,

                power_to=280,

                cadence_from=85,

                cadence_to=95,

                repeat=1,

                description="",

            )

        ],

    )


    start = datetime.now()


    records = []

    for second in range(300):

        records.append(

            ActivityRecord(

                timestamp=start + timedelta(seconds=second),

                elapsed_time=second,

                power=260,

                heart_rate=150,

                cadence=90,

                speed=35,

            )

        )


    activity = Activity(

        start=start,

        end=start + timedelta(seconds=300),

        sport="cycling",

        distance=5,

        calories=150,

        duration=300,

        records=records,

    )


    summary = WorkoutAnalyzer().analyze(

        activity,

    )


    timeline = TimelineBuilder().build(

        workout,

    )


    context = ExecutionContext(

        workout=workout,

        activity=activity,

        summary=summary,

        timeline=timeline,

    )


    result = ExecutionEngine().analyze_context(

        context,

    )


    assert isinstance(

        result,

        ExecutionResult,

    )


    assert result.completed is True


    assert result.execution_score > 0


    assert result.executed_tss > 0


    assert len(result.blocks) == 1


    assert result.blocks[0].execution_score > 0