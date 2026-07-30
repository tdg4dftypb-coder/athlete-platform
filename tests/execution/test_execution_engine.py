from execution.engine import ExecutionEngine
from execution.result import ExecutionResult

from training.analysis.workout_summary import WorkoutSummary

from workout.models import Workout


def test_execution_engine_returns_execution_result():

    workout = Workout(

        name="Threshold 4x8",

        goal="FTP development",

        description="",

        duration=60,

        target_tss=80,

        target_if=0.95,

        blocks=[],

    )


    activity = WorkoutSummary(

        start=None,

        end=None,

        sport="cycling",

        duration=3600,

        distance=40,

        calories=800,

        average_power=250,

        normalized_power=260,

        max_power=500,

        intensity_factor=0.90,

        tss=75,

        average_hr=150,

        max_hr=170,

        average_cadence=90,

        max_cadence=110,

        zones=None,

    )


    result = ExecutionEngine().analyze(

        workout,

        activity,

    )


    assert isinstance(

        result,

        ExecutionResult,

    )


    assert result.planned_duration == 60

    assert result.executed_duration == 60


    assert result.planned_tss == 80

    assert result.executed_tss == 75


    assert result.execution_score > 90

    assert result.completed is True


    assert (
        "Workout completed"
        in result.insights
    )