from execution.result import (
    BlockExecutionResult,
    ExecutionResult,
)


def test_execution_result_contract():

    block = BlockExecutionResult(

        name="VO2 Interval",

        planned_duration=300,

        executed_duration=295,

        completion_score=98.0,

        power_score=95.0,

        cadence_score=None,

        heart_rate_score=None,

        execution_score=96.0,

        deviations=[
            "Cadence data unavailable",
        ],

    )


    result = ExecutionResult(

        planned_duration=75,

        executed_duration=74,

        planned_tss=85,

        executed_tss=82,

        completion_score=98.0,

        power_score=None,

        cadence_score=None,

        heart_rate_score=None,

        execution_score=97.0,

        completed=True,

        blocks=[
            block,
        ],

        insights=[
            "Workout completed successfully",
        ],

    )


    assert result.planned_duration == 75

    assert result.executed_duration == 74

    assert result.planned_tss == 85

    assert result.executed_tss == 82

    assert result.execution_score == 97.0

    assert result.completed is True


    assert result.power_score is None

    assert result.cadence_score is None

    assert result.heart_rate_score is None


    assert len(result.blocks) == 1

    assert result.blocks[0].name == "VO2 Interval"

    assert (
        result.insights
        ==
        [
            "Workout completed successfully",
        ]
    )