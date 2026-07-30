from datetime import datetime

from execution.block_analyzer import BlockAnalyzer
from execution.result import BlockExecutionResult

from timeline.models import TimelineBlock

from training.activity import (
    Activity,
    ActivityRecord,
)


def test_block_analyzer_returns_block_execution_result():

    block = TimelineBlock(

        index=1,

        name="VO2 Interval",

        start=0,

        end=300,

        duration=300,

        power_from=250,

        power_to=280,

        cadence_from=85,

        cadence_to=95,

        repeat=1,

        description="",

    )


    records = [

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

            heart_rate=165,

            cadence=91,

            speed=35,

        ),

    ]


    activity = Activity(

        start=datetime.now(),

        end=datetime.now(),

        sport="cycling",

        distance=5,

        calories=150,

        duration=300,

        records=records,

    )


    result = BlockAnalyzer().analyze(

        block,

        activity,

    )


    assert isinstance(

        result,

        BlockExecutionResult,

    )


    assert result.name == "VO2 Interval"


    assert result.planned_duration == 300


    assert result.executed_duration == 299


    assert result.completion_score > 0


    assert result.power_score is not None


    assert result.cadence_score is not None


    assert result.execution_score > 0