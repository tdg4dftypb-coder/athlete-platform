from pathlib import Path
import sys
from typing import Optional, Union

from decision.persistence import DuckDbDecisionAuditRecordRepository
from decision.persistence.paths import get_default_decisions_db_path
from decision.runtime_persistence_composition import create_persisted_decision_runtime_application
from morning_briefing.provider import EmptyMorningBriefingInputProvider
from performance_lab.provider import EmptyPerformanceTestHistoryProvider


def run_decision_runtime(
    db_path: Optional[Union[str, Path]] = None,
    morning_briefing_provider=None,
    performance_history_provider=None,
) -> int:
    """Explicit CLI runner for Decision Intelligence 2.0 runtime workflow."""
    mb_provider = morning_briefing_provider or EmptyMorningBriefingInputProvider()
    perf_provider = performance_history_provider or EmptyPerformanceTestHistoryProvider()
    target_path = get_default_decisions_db_path(db_path)

    try:
        repo = DuckDbDecisionAuditRecordRepository(db_path=str(target_path))
        app = create_persisted_decision_runtime_application(
            morning_briefing_provider=mb_provider,
            performance_history_provider=perf_provider,
            repository=repo,
        )

        result = app.workflow.run()
        record = result.record

        print("Decision generated")
        print(f"Decision ID : {record.decision_id}")
        print(f"Action      : {record.policy_result.action.value}")
        print(f"Severity    : {record.policy_result.severity.value}")
        print(f"Confidence  : {record.policy_result.confidence:.2f}")
        print(f"Generated   : {record.context.generated_at.isoformat()}")

        return 0
    except Exception as err:
        print(f"Error executing Decision Runtime: {type(err).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_decision_runtime())
