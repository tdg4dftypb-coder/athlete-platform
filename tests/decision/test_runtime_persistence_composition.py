import duckdb
import pytest

from decision import (
    DuckDbDecisionAuditRecordRepository,
    create_persisted_decision_runtime_application,
)
from tests.decision.test_decision_runtime_composition import (
    CountingMorningBriefingProvider,
    CountingPerformanceHistoryProvider,
)


def test_runtime_persistence_composition_end_to_end():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    mb_provider = CountingMorningBriefingProvider()
    perf_provider = CountingPerformanceHistoryProvider()

    app = create_persisted_decision_runtime_application(
        morning_briefing_provider=mb_provider,
        performance_history_provider=perf_provider,
        repository=repo,
    )

    # 1. Before run: latest_provider returns None
    assert app.latest_provider.get_latest_record() is None

    # 2. Run workflow
    result = app.workflow.run()

    # 3. After run: latest_provider returns saved record
    assert app.latest_provider.get_latest_record() == result.record
    assert repo.get_by_id(result.record.decision_id) == result.record

    # 4. Verify Morning Briefing provider call count (1 call for snapshot + 3 fallback calls from default adapters)
    assert mb_provider.call_count == 4
    assert perf_provider.call_count == 1
