import duckdb
import pytest

from decision import (
    DuckDbDecisionAuditRecordRepository,
    PersistedDecisionRuntimeWorkflow,
    create_decision_runtime_workflow,
)
from tests.decision.test_decision_record_codec import build_sample_record
from tests.decision.test_decision_runtime_composition import (
    CountingMorningBriefingProvider,
    CountingPerformanceHistoryProvider,
)


def test_persisted_workflow_runs_and_saves_record():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)

    inner_workflow = create_decision_runtime_workflow(
        morning_briefing_provider=CountingMorningBriefingProvider(),
        performance_history_provider=CountingPerformanceHistoryProvider(),
    )

    persisted = PersistedDecisionRuntimeWorkflow(
        runtime_workflow=inner_workflow,
        repository=repo,
    )

    # 1. Run workflow
    result = persisted.run()

    # 2. Verify record is saved in repository
    saved = repo.get_by_id(result.record.decision_id)
    assert saved == result.record
    assert repo.get_latest() == result.record


def test_persisted_workflow_error_in_workflow_does_not_call_save():
    class FailingWorkflow:
        def run(self):
            raise RuntimeError("Workflow failed")

    class MockRepo:
        def __init__(self):
            self.save_called = False

        def save(self, record):
            self.save_called = True

    repo = MockRepo()
    persisted = PersistedDecisionRuntimeWorkflow(
        runtime_workflow=FailingWorkflow(),
        repository=repo,
    )

    with pytest.raises(RuntimeError, match="Workflow failed"):
        persisted.run()

    assert repo.save_called is False
