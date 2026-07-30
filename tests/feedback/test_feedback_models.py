from dataclasses import FrozenInstanceError

import pytest

from feedback.models import (
    FeedbackSignal,
    WorkoutFeedback,
    WorkoutFeedbackStatus,
)


def test_feedback_models_are_immutable():

    signal = FeedbackSignal(
        code="SESSION_COMPLETED",
        message="Trening został ukończony.",
    )

    feedback = WorkoutFeedback(
        status=WorkoutFeedbackStatus.COMPLETED,
        headline="Trening wykonany",
        summary="Plan treningowy został zrealizowany.",
        execution_score=92.0,
        completion_score=95.0,
        positive_signals=(signal,),
        attention_signals=(),
    )

    with pytest.raises(FrozenInstanceError):
        feedback.status = WorkoutFeedbackStatus.PARTIAL

    with pytest.raises(FrozenInstanceError):
        signal.code = "SESSION_PARTIAL"


def test_feedback_status_values_are_stable():

    assert WorkoutFeedbackStatus.EXCELLENT.value == "excellent"
    assert WorkoutFeedbackStatus.COMPLETED.value == "completed"
    assert WorkoutFeedbackStatus.PARTIAL.value == "partial"
    assert WorkoutFeedbackStatus.INTERRUPTED.value == "interrupted"
