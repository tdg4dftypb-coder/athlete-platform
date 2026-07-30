from datetime import datetime

from execution.context import ExecutionContext

from timeline.models import WorkoutTimeline

from training.activity import Activity

from training.analysis.workout_summary import WorkoutSummary

from workout.models import Workout


def test_execution_context_contract():

    workout = Workout(

        name="VO2 Test",

        goal="VO2max",

        description="",

        duration=60,

        target_tss=85,

        target_if=1.0,

        blocks=[],

    )


    activity = Activity(

        start=datetime.now(),

        end=datetime.now(),

        sport="cycling",

        distance=20,

        calories=500,

        duration=3600,

        records=[],

    )


    summary = WorkoutSummary(

        start=datetime.now(),

        end=datetime.now(),

        sport="cycling",

        duration=3600,

        distance=20,

        calories=500,

        average_power=250,

        normalized_power=260,

        max_power=500,

        intensity_factor=0.95,

        tss=85,

        average_hr=150,

        max_hr=170,

        average_cadence=90,

        max_cadence=110,

    )


    timeline = WorkoutTimeline(

        blocks=[],

        total_duration=3600,

    )


    context = ExecutionContext(

        workout=workout,

        activity=activity,

        summary=summary,

        timeline=timeline,

    )


    assert context.workout == workout

    assert context.activity == activity

    assert context.summary == summary

    assert context.timeline == timeline