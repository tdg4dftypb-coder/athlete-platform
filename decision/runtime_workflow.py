from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
import uuid

from decision.execution_service import DecisionExecutionRequest, DecisionExecutionResult, DecisionExecutionService


@runtime_checkable
class DecisionClock(Protocol):
    """Protocol boundary for retrieving current datetime."""

    def now(self) -> datetime:
        ...


class SystemUtcDecisionClock:
    """Concrete clock implementation returning timezone-aware UTC datetime."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@runtime_checkable
class DecisionIdGenerator(Protocol):
    """Protocol boundary for generating domain decision identifiers."""

    def generate(self) -> str:
        ...


class UuidDecisionIdGenerator:
    """Concrete generator producing decision-<uuid4> string identifiers."""

    def generate(self) -> str:
        return f"decision-{uuid.uuid4()}"


class DecisionRuntimeWorkflow:
    """Stateless application workflow driving decision execution timing and ID generation."""

    def __init__(
        self,
        execution_service: DecisionExecutionService,
        clock: DecisionClock | None = None,
        id_generator: DecisionIdGenerator | None = None,
    ) -> None:
        if execution_service is None:
            raise TypeError("execution_service must not be None")

        self._execution_service = execution_service
        self._clock = clock or SystemUtcDecisionClock()
        self._id_generator = id_generator or UuidDecisionIdGenerator()

    def run(self) -> DecisionExecutionResult:
        # 1. Capture generated_at timestamp
        generated_at = self._clock.now()

        # 2. Generate decision identifier
        decision_id = self._id_generator.generate()

        # 3. Capture recorded_at timestamp
        recorded_at = self._clock.now()

        # 4. Construct explicit execution request
        request = DecisionExecutionRequest(
            decision_id=decision_id,
            generated_at=generated_at,
            recorded_at=recorded_at,
        )

        # 5. Execute pipeline and return result
        return self._execution_service.execute(request)
