from datetime import datetime, timezone
import uuid
import pytest

from decision import (
    DecisionClock,
    DecisionExecutionRequest,
    DecisionIdGenerator,
    DecisionRuntimeWorkflow,
    SystemUtcDecisionClock,
    UuidDecisionIdGenerator,
)


class StubClock:
    def __init__(self, timestamps: list[datetime]):
        self.timestamps = list(timestamps)
        self.call_count = 0

    def now(self) -> datetime:
        self.call_count += 1
        return self.timestamps.pop(0)


class StubIdGenerator:
    def __init__(self, ids: list[str]):
        self.ids = list(ids)
        self.call_count = 0

    def generate(self) -> str:
        self.call_count += 1
        return self.ids.pop(0)


class SpyExecutionService:
    def __init__(self, return_result=None, raise_error=None):
        self.return_result = return_result
        self.raise_error = raise_error
        self.last_request = None
        self.call_count = 0

    def execute(self, request: DecisionExecutionRequest):
        self.call_count += 1
        self.last_request = request
        if self.raise_error:
            raise self.raise_error
        return self.return_result


def test_system_utc_decision_clock():
    clock = SystemUtcDecisionClock()
    t1 = clock.now()
    t2 = clock.now()

    assert isinstance(t1, datetime)
    assert t1.tzinfo == timezone.utc
    assert isinstance(t2, datetime)
    assert t2.tzinfo == timezone.utc


def test_uuid_decision_id_generator():
    gen = UuidDecisionIdGenerator()
    id1 = gen.generate()
    id2 = gen.generate()

    assert id1.startswith("decision-")
    assert id2.startswith("decision-")
    assert id1 != id2
    # Verify suffix is valid UUID
    uuid_part = id1[len("decision-"):]
    assert uuid.UUID(uuid_part)


def test_decision_runtime_workflow_execution():
    t_gen = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)
    t_rec = datetime(2026, 8, 6, 12, 0, 1, tzinfo=timezone.utc)
    clock = StubClock([t_gen, t_rec])
    id_gen = StubIdGenerator(["decision-stub-01"])

    expected_result = object()
    spy_service = SpyExecutionService(return_result=expected_result)

    workflow = DecisionRuntimeWorkflow(
        execution_service=spy_service,  # type: ignore
        clock=clock,
        id_generator=id_gen,
    )

    res = workflow.run()

    assert res is expected_result
    assert clock.call_count == 2
    assert id_gen.call_count == 1
    assert spy_service.call_count == 1
    assert spy_service.last_request.decision_id == "decision-stub-01"
    assert spy_service.last_request.generated_at == t_gen
    assert spy_service.last_request.recorded_at == t_rec


def test_decision_runtime_workflow_error_propagation():
    # Clock 1 failure
    class FailingClock:
        def now(self):
            raise RuntimeError("Clock failed")

    spy_service = SpyExecutionService()
    workflow = DecisionRuntimeWorkflow(
        execution_service=spy_service,  # type: ignore
        clock=FailingClock(),
    )

    with pytest.raises(RuntimeError, match="Clock failed"):
        workflow.run()

    assert spy_service.call_count == 0
