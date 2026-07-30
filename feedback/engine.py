from execution.result import ExecutionResult
from feedback.models import (
    FeedbackSignal,
    WorkoutFeedback,
    WorkoutFeedbackStatus,
)


class WorkoutFeedbackEngine:

    TIME_TARGET_SCORE = 90
    LOAD_TARGET_RATIO = 0.90
    EXECUTION_TARGET_SCORE = 90

    def build(
        self,
        execution: ExecutionResult,
    ) -> WorkoutFeedback:

        status = self._classify(execution)

        positive_signals = []
        attention_signals = []

        self._add_session_signal(
            status,
            positive_signals,
            attention_signals,
        )

        self._add_time_signal(
            execution,
            positive_signals,
            attention_signals,
        )

        self._add_load_signal(
            execution,
            positive_signals,
            attention_signals,
        )

        self._add_block_signals(
            execution,
            attention_signals,
        )

        if execution.execution_score < self.EXECUTION_TARGET_SCORE:
            attention_signals.append(
                FeedbackSignal(
                    code="EXECUTION_BELOW_TARGET",
                    message=(
                        "Wynik wykonania jest poniżej "
                        "docelowego poziomu."
                    ),
                )
            )

        headline, summary = self._copy_for(status)

        return WorkoutFeedback(
            status=status,
            headline=headline,
            summary=summary,
            execution_score=execution.execution_score,
            completion_score=execution.completion_score,
            positive_signals=tuple(positive_signals),
            attention_signals=tuple(attention_signals),
        )

    @staticmethod
    def _classify(
        execution: ExecutionResult,
    ) -> WorkoutFeedbackStatus:

        if execution.completion_score < 50:
            return WorkoutFeedbackStatus.INTERRUPTED

        if (
            execution.completion_score < 90
            or not execution.completed
            or any(
                block.completion_score == 0
                for block in execution.blocks
            )
        ):
            return WorkoutFeedbackStatus.PARTIAL

        if (
            execution.completed
            and execution.completion_score >= 95
            and execution.execution_score >= 95
            and not any(
                block.completion_score == 0
                for block in execution.blocks
            )
        ):
            return WorkoutFeedbackStatus.EXCELLENT

        return WorkoutFeedbackStatus.COMPLETED

    @staticmethod
    def _add_session_signal(
        status: WorkoutFeedbackStatus,
        positive_signals: list[FeedbackSignal],
        attention_signals: list[FeedbackSignal],
    ) -> None:

        if status == WorkoutFeedbackStatus.EXCELLENT:
            positive_signals.extend(
                (
                    FeedbackSignal(
                        code="SESSION_COMPLETED",
                        message="Trening został ukończony.",
                    ),
                    FeedbackSignal(
                        code="SESSION_EXCELLENT",
                        message="Trening został wykonany bardzo dobrze.",
                    ),
                )
            )
            return

        if status == WorkoutFeedbackStatus.COMPLETED:
            positive_signals.append(
                FeedbackSignal(
                    code="SESSION_COMPLETED",
                    message="Trening został ukończony.",
                )
            )
            return

        if status == WorkoutFeedbackStatus.PARTIAL:
            attention_signals.append(
                FeedbackSignal(
                    code="SESSION_PARTIAL",
                    message="Trening został wykonany częściowo.",
                )
            )
            return

        attention_signals.append(
            FeedbackSignal(
                code="SESSION_INTERRUPTED",
                message="Trening został przerwany.",
            )
        )

    def _add_time_signal(
        self,
        execution: ExecutionResult,
        positive_signals: list[FeedbackSignal],
        attention_signals: list[FeedbackSignal],
    ) -> None:

        if execution.completion_score >= self.TIME_TARGET_SCORE:
            positive_signals.append(
                FeedbackSignal(
                    code="PLAN_TIME_ACHIEVED",
                    message="Zrealizowano planowany czas treningu.",
                )
            )
            return

        attention_signals.append(
            FeedbackSignal(
                code="PLAN_TIME_BELOW_TARGET",
                message="Czas treningu był niższy od planowanego.",
            )
        )

    def _add_load_signal(
        self,
        execution: ExecutionResult,
        positive_signals: list[FeedbackSignal],
        attention_signals: list[FeedbackSignal],
    ) -> None:

        load_achieved = (
            execution.planned_tss <= 0
            or execution.executed_tss
            >= execution.planned_tss * self.LOAD_TARGET_RATIO
        )

        if load_achieved:
            positive_signals.append(
                FeedbackSignal(
                    code="PLAN_LOAD_ACHIEVED",
                    message="Zrealizowano planowane obciążenie treningowe.",
                )
            )
            return

        attention_signals.append(
            FeedbackSignal(
                code="PLAN_LOAD_BELOW_TARGET",
                message="Obciążenie treningowe było niższe od planowanego.",
            )
        )

    @staticmethod
    def _add_block_signals(
        execution: ExecutionResult,
        attention_signals: list[FeedbackSignal],
    ) -> None:

        for block in execution.blocks:

            if block.completion_score == 0:
                attention_signals.append(
                    FeedbackSignal(
                        code="BLOCK_NOT_COMPLETED",
                        message=f"Nie wykonano bloku: {block.name}.",
                        block_name=block.name,
                    )
                )

    @staticmethod
    def _copy_for(
        status: WorkoutFeedbackStatus,
    ) -> tuple[str, str]:

        copy = {
            WorkoutFeedbackStatus.EXCELLENT: (
                "Świetnie wykonany trening",
                "Plan został zrealizowany z bardzo wysoką jakością.",
            ),
            WorkoutFeedbackStatus.COMPLETED: (
                "Trening wykonany",
                "Plan treningowy został zrealizowany.",
            ),
            WorkoutFeedbackStatus.PARTIAL: (
                "Trening wykonany częściowo",
                "Nie wszystkie elementy planu zostały zrealizowane.",
            ),
            WorkoutFeedbackStatus.INTERRUPTED: (
                "Trening przerwany",
                "Trening zakończył się przed realizacją większości planu.",
            ),
        }

        return copy[status]
