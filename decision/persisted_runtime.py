from decision.execution_service import DecisionExecutionResult
from decision.repository import DecisionAuditRecordRepository
from decision.runtime_workflow import DecisionRuntimeWorkflow


class PersistedDecisionRuntimeWorkflow:
    """Decorator workflow executing DecisionRuntimeWorkflow and persisting the resulting DecisionAuditRecord."""

    def __init__(
        self,
        runtime_workflow: DecisionRuntimeWorkflow,
        repository: DecisionAuditRecordRepository,
    ) -> None:
        if runtime_workflow is None:
            raise TypeError("runtime_workflow must not be None")
        if repository is None:
            raise TypeError("repository must not be None")

        self._runtime_workflow = runtime_workflow
        self._repository = repository

    def run(self) -> DecisionExecutionResult:
        # 1. Execute runtime pipeline
        result = self._runtime_workflow.run()

        # 2. Persist audit record atomically
        self._repository.save(result.record)

        # 3. Return unchanged result
        return result
