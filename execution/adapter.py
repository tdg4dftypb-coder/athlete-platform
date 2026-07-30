from execution.models import ExecutionState

from execution.result import ExecutionResult


class ExecutionAdapter:

    @staticmethod
    def from_state(
        state: ExecutionState,
    ) -> ExecutionResult:

        return ExecutionResult(

            planned_duration=state.planned_duration,

            executed_duration=state.executed_duration,

            planned_tss=state.planned_tss,

            executed_tss=state.executed_tss,

            completion_score=state.duration_score,

            power_score=None,

            cadence_score=None,

            heart_rate_score=None,

            execution_score=state.overall_score,

            completed=state.completed,

            insights=list(
                state.reasons,
            ),

        )