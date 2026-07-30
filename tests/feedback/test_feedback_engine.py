import pytest

from execution.result import BlockExecutionResult, ExecutionResult
from feedback.engine import WorkoutFeedbackEngine
from feedback.models import WorkoutFeedbackStatus


def build_execution(
    *,
    completion_score: float = 100.0,
    execution_score: float = 95.0,
    completed: bool = True,
    planned_tss: float = 80.0,
    executed_tss: float = 80.0,
    blocks: list[BlockExecutionResult] | None = None,
) -> ExecutionResult:

    return ExecutionResult(
        planned_duration=60,
        executed_duration=60,
        planned_tss=planned_tss,
        executed_tss=executed_tss,
        completion_score=completion_score,
        power_score=None,
        cadence_score=None,
        heart_rate_score=None,
        execution_score=execution_score,
        completed=completed,
        blocks=blocks or [],
        insights=[],
    )


def incomplete_block() -> BlockExecutionResult:

    return BlockExecutionResult(
        name="VO2 Interval",
        planned_duration=300,
        executed_duration=0,
        completion_score=0,
        power_score=None,
        cadence_score=None,
        heart_rate_score=None,
        execution_score=0,
        deviations=["Block not completed."],
    )


def signal_codes(signals) -> set[str]:

    return {signal.code for signal in signals}


def assert_signal_codes(
    feedback,
    *,
    positive: set[str],
    attention: set[str],
) -> None:

    assert signal_codes(feedback.positive_signals) == positive
    assert signal_codes(feedback.attention_signals) == attention


def test_classifies_excellent_training():

    feedback = WorkoutFeedbackEngine().build(build_execution())

    assert feedback.status == WorkoutFeedbackStatus.EXCELLENT
    assert_signal_codes(
        feedback,
        positive={
            "SESSION_COMPLETED",
            "SESSION_EXCELLENT",
            "PLAN_TIME_ACHIEVED",
            "PLAN_LOAD_ACHIEVED",
        },
        attention=set(),
    )


def test_classifies_regular_completed_training():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=90,
            execution_score=92,
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.COMPLETED
    assert_signal_codes(
        feedback,
        positive={
            "SESSION_COMPLETED",
            "PLAN_TIME_ACHIEVED",
            "PLAN_LOAD_ACHIEVED",
        },
        attention=set(),
    )


@pytest.mark.parametrize("completion_score", [50.0, 89.99])
def test_classifies_partial_training_between_50_and_89(
    completion_score: float,
):

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=completion_score,
            execution_score=95,
            completed=True,
            executed_tss=80,
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.PARTIAL
    assert_signal_codes(
        feedback,
        positive={"PLAN_LOAD_ACHIEVED"},
        attention={
            "SESSION_PARTIAL",
            "PLAN_TIME_BELOW_TARGET",
        },
    )


def test_classifies_partial_training_with_incomplete_block():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=95,
            execution_score=95,
            blocks=[incomplete_block()],
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.PARTIAL
    assert_signal_codes(
        feedback,
        positive={
            "PLAN_TIME_ACHIEVED",
            "PLAN_LOAD_ACHIEVED",
        },
        attention={
            "SESSION_PARTIAL",
            "BLOCK_NOT_COMPLETED",
        },
    )


def test_classifies_interrupted_training_below_50():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=49.99,
            execution_score=95,
            completed=True,
            executed_tss=80,
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.INTERRUPTED
    assert_signal_codes(
        feedback,
        positive={"PLAN_LOAD_ACHIEVED"},
        attention={
            "SESSION_INTERRUPTED",
            "PLAN_TIME_BELOW_TARGET",
        },
    )


def test_adds_signal_for_each_incomplete_block():

    block = incomplete_block()

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=95,
            execution_score=95,
            blocks=[block],
        )
    )

    signal = next(
        signal
        for signal in feedback.attention_signals
        if signal.code == "BLOCK_NOT_COMPLETED"
    )

    assert signal.message == "Nie wykonano bloku: VO2 Interval."
    assert signal.block_name == "VO2 Interval"


def test_separates_positive_and_attention_signals():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=80,
            execution_score=80,
            completed=False,
            executed_tss=80,
        )
    )

    assert "PLAN_LOAD_ACHIEVED" in signal_codes(
        feedback.positive_signals
    )
    assert "SESSION_PARTIAL" in signal_codes(
        feedback.attention_signals
    )
    assert "PLAN_TIME_BELOW_TARGET" in signal_codes(
        feedback.attention_signals
    )
    assert "EXECUTION_BELOW_TARGET" in signal_codes(
        feedback.attention_signals
    )


def test_classification_boundaries_90_and_95():

    completed = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=90,
            execution_score=94.9,
        )
    )
    excellent = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=95,
            execution_score=95,
        )
    )

    assert completed.status == WorkoutFeedbackStatus.COMPLETED
    assert excellent.status == WorkoutFeedbackStatus.EXCELLENT


def test_completed_false_blocks_excellent_classification():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=95,
            execution_score=95,
            completed=False,
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.PARTIAL
    assert_signal_codes(
        feedback,
        positive={
            "PLAN_TIME_ACHIEVED",
            "PLAN_LOAD_ACHIEVED",
        },
        attention={"SESSION_PARTIAL"},
    )


def test_interrupted_has_priority_over_incomplete_block():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            completion_score=49.99,
            execution_score=95,
            blocks=[incomplete_block()],
        )
    )

    assert feedback.status == WorkoutFeedbackStatus.INTERRUPTED
    assert_signal_codes(
        feedback,
        positive={"PLAN_LOAD_ACHIEVED"},
        attention={
            "SESSION_INTERRUPTED",
            "PLAN_TIME_BELOW_TARGET",
            "BLOCK_NOT_COMPLETED",
        },
    )


def test_load_at_90_percent_is_achieved():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            planned_tss=100,
            executed_tss=90,
        )
    )

    assert "PLAN_LOAD_ACHIEVED" in signal_codes(
        feedback.positive_signals
    )
    assert "PLAN_LOAD_BELOW_TARGET" not in signal_codes(
        feedback.attention_signals
    )


def test_load_below_90_percent_requires_attention():

    feedback = WorkoutFeedbackEngine().build(
        build_execution(
            planned_tss=100,
            executed_tss=89.99,
        )
    )

    assert "PLAN_LOAD_ACHIEVED" not in signal_codes(
        feedback.positive_signals
    )
    assert "PLAN_LOAD_BELOW_TARGET" in signal_codes(
        feedback.attention_signals
    )
