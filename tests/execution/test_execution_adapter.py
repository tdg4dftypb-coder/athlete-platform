from execution.adapter import ExecutionAdapter
from execution.models import ExecutionState


def test_execution_adapter_converts_state():

    state = ExecutionState(

        planned_duration=60,

        executed_duration=58,

        duration_score=96.0,

        planned_tss=80,

        executed_tss=75,

        tss_score=93.75,

        overall_score=94.9,

        completed=True,

        reasons=[
            "Workout completed",
        ],
    )


    result = ExecutionAdapter.from_state(
        state,
    )


    assert result.planned_duration == 60

    assert result.executed_duration == 58

    assert result.planned_tss == 80

    assert result.executed_tss == 75

    assert result.execution_score == 94.9

    assert result.completed is True

    assert (
        result.insights
        ==
        [
            "Workout completed",
        ]
    )