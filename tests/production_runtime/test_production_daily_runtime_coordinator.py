from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest

from production_runtime.coordinator import (
    MISSING_TRAINING_PLAN,
    ProductionDailyRuntime,
    RuntimeAttemptNotResumableError,
    RuntimePhaseError,
    RuntimePhaseOutcome,
)
from production_runtime.models import PhaseStatus, RuntimePhase, RuntimeStatus, SourceWatermark
from production_runtime.persistence import DuckDbRuntimeAuditRepository


@dataclass
class Clock:
    tick: int = 0
    def now_utc(self):
        self.tick += 1
        return datetime(2026, 8, 11, 4, 0, self.tick, tzinfo=timezone.utc)


class Adapter:
    def __init__(self, outcome=None, error=None):
        self.outcome = outcome or RuntimePhaseOutcome()
        self.error = error
        self.calls = 0
    def execute(self, context):
        self.calls += 1
        if self.error:
            raise self.error
        return self.outcome


def adapters():
    values = {phase: Adapter() for phase in RuntimePhase}
    values[RuntimePhase.INGESTION] = Adapter(RuntimePhaseOutcome(
        activities_discovered=0,
        source_watermarks=(SourceWatermark("fit", "snapshot", "empty"),),
    ))
    values[RuntimePhase.RECONCILIATION] = Adapter(RuntimePhaseOutcome(
        status=PhaseStatus.SKIPPED,
        warning_codes=("reconciliation_not_applicable",),
        reconciliations_created=0,
    ))
    values[RuntimePhase.DECISION] = Adapter(RuntimePhaseOutcome(decision_id="decision-1"))
    values[RuntimePhase.PLAN_PRESCRIPTION] = Adapter(RuntimePhaseOutcome(
        training_plan_id="plan-1", prescription_id="rx-1"
    ))
    values[RuntimePhase.MORNING_BRIEFING] = Adapter(RuntimePhaseOutcome(
        artifact_ids=("briefing:sha256:abc",), morning_briefing_available=True
    ))
    values[RuntimePhase.PUBLICATION] = Adapter(RuntimePhaseOutcome(
        artifact_ids=("decision-1", "plan-1", "rx-1")
    ))
    return values


def build(tmp_path, phase_adapters=None):
    repo = DuckDbRuntimeAuditRepository(tmp_path / "runtime.duckdb")
    return ProductionDailyRuntime(
        repo, phase_adapters or adapters(), clock=Clock(), runtime_id_factory=lambda: "runtime-1"
    ), repo


def test_success_has_revision_per_phase_plus_initial_and_terminal(tmp_path):
    runtime, repo = build(tmp_path)
    result = runtime.run_new_attempt(date(2026, 8, 11))
    assert result.status is RuntimeStatus.COMPLETED
    assert result.revision == 10
    assert tuple(p.phase for p in result.phases) == tuple(RuntimePhase)
    assert result.decision_id == "decision-1"
    assert result.training_plan_id == "plan-1"
    assert result.prescription_id == "rx-1"
    assert result.morning_briefing_available
    assert repo.get_by_runtime_id("runtime-1") == result


def test_missing_plan_is_stable_partial_and_does_not_run_later_phases(tmp_path):
    values = adapters()
    values[RuntimePhase.DECISION] = Adapter(error=RuntimePhaseError(MISSING_TRAINING_PLAN))
    runtime, _ = build(tmp_path, values)
    result = runtime.run_new_attempt(date(2026, 8, 11))
    assert result.status is RuntimeStatus.PARTIAL
    assert result.failure.code == MISSING_TRAINING_PLAN
    assert result.phases[-1].phase is RuntimePhase.DECISION
    assert values[RuntimePhase.PLAN_PRESCRIPTION].calls == 0


def test_failure_before_first_phase_is_failed(tmp_path):
    values = adapters()
    values[RuntimePhase.INGESTION] = Adapter(error=OSError("missing"))
    runtime, _ = build(tmp_path, values)
    result = runtime.run_new_attempt(date(2026, 8, 11))
    assert result.status is RuntimeStatus.FAILED
    assert result.failure.code == "phase_interrupted"


def test_resume_skips_every_durable_phase(tmp_path):
    values = adapters()
    values[RuntimePhase.ASSESSMENT] = Adapter(error=KeyboardInterrupt())
    runtime, repo = build(tmp_path, values)
    with pytest.raises(KeyboardInterrupt):
        runtime.run_new_attempt(date(2026, 8, 11))
    assert repo.get_by_runtime_id("runtime-1").revision == 4
    before = {phase: adapter.calls for phase, adapter in values.items()}
    values[RuntimePhase.ASSESSMENT].error = None
    result = runtime.resume_attempt("runtime-1")
    assert result.status is RuntimeStatus.COMPLETED
    for phase in tuple(RuntimePhase)[:3]:
        assert values[phase].calls == before[phase]


def test_terminal_attempt_cannot_resume(tmp_path):
    runtime, _ = build(tmp_path)
    runtime.run_new_attempt(date(2026, 8, 11))
    with pytest.raises(RuntimeAttemptNotResumableError):
        runtime.resume_attempt("runtime-1")


def test_resume_after_persisted_assessment_is_honestly_unsupported(tmp_path):
    values = adapters()
    values[RuntimePhase.DECISION] = Adapter(error=KeyboardInterrupt())
    runtime, _ = build(tmp_path, values)
    with pytest.raises(KeyboardInterrupt):
        runtime.run_new_attempt(date(2026, 8, 11))
    with pytest.raises(RuntimeAttemptNotResumableError, match="assessment snapshot"):
        runtime.resume_attempt("runtime-1")


def test_independent_attempts_share_logical_date_key(tmp_path):
    repo = DuckDbRuntimeAuditRepository(tmp_path / "runtime.duckdb")
    ids = iter(("runtime-1", "runtime-2"))
    runtime = ProductionDailyRuntime(repo, adapters(), clock=Clock(), runtime_id_factory=lambda: next(ids))
    one = runtime.run_new_attempt(date(2026, 8, 11))
    two = runtime.run_new_attempt(date(2026, 8, 11))
    assert one.logical_execution_key == two.logical_execution_key
    assert one.runtime_id != two.runtime_id
