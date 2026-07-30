from datetime import datetime

from execution.context import ExecutionContext
from execution.engine import ExecutionEngine
from execution.result import ExecutionResult

from timeline.builder import TimelineBuilder

from training.activity import (
    Activity,
    ActivityRecord,
)

from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.models import Workout
from workout.blocks import WorkoutBlock


def test_execution_engine_context_builds_block_results():

    workout = Workout(

        name="VO2 Test",

        goal="VO2max",

        description="",

        duration=5,

        target_tss=20,

        target_if=1.0,

        blocks=[

            WorkoutBlock(

                name="VO2 Interval",

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


    activity = Activity(

        start=datetime.now(),

        end=datetime.now(),

        sport="cycling",

        distance=5,

        calories=150,

        duration=300,

        records=[

            ActivityRecord(

                timestamp=datetime.now(),

                elapsed_time=0,

                power=260,

                heart_rate=150,

                cadence=90,

                speed=35,

            ),

            ActivityRecord(

                timestamp=datetime.now(),

                elapsed_time=299,

                power=270,

                heart_rate=160,

                cadence=91,

                speed=35,

            ),

        ],

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


    assert len(result.blocks) == 1


    block = result.blocks[0]


    assert block.name == "VO2 Interval"

    assert block.execution_score > 0

    assert block.power_score is not None

    assert block.cadence_score is not None