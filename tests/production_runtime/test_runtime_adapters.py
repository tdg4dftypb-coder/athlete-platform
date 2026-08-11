from datetime import datetime, timezone

import pytest

from morning_briefing.input_models import MorningBriefingInput
from production_runtime.adapters import (
    AssessmentSnapshotAdapter,
    FrozenMorningBriefingInputProvider,
    MorningBriefingProofAdapter,
    PersistedAssessmentSnapshotProvider,
    PublicationValidationAdapter,
)
from production_runtime.coordinator import RuntimePhaseContext, RuntimePhaseError
from production_runtime.models import (
    ProductionDailyRuntimeResult,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    logical_execution_key,
)
from datetime import date
from production_runtime.models import PhaseStatus
from production_runtime.persistence import DuckDbAssessmentSnapshotRepository


class Provider:
    calls = 0
    def get_input(self):
        self.calls += 1
        return MorningBriefingInput(
            generated_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
            recovery=None, training=None, biomarkers=None,
        )


def running(**changes):
    values = dict(
        runtime_id="runtime-1", logical_execution_key=logical_execution_key(date(2026, 8, 11)),
        revision=1, contract_version="1.0", target_local_date=date(2026, 8, 11),
        timezone_name="Europe/Warsaw", started_at_utc=datetime(2026, 8, 11, tzinfo=timezone.utc),
        completed_at_utc=None, status=RuntimeStatus.RUNNING,
    )
    values.update(changes)
    return ProductionDailyRuntimeResult(**values)


def test_assessment_and_briefing_use_one_frozen_input():
    source = Provider()
    frozen = FrozenMorningBriefingInputProvider(source)
    context = RuntimePhaseContext(running())
    assessment = AssessmentSnapshotAdapter(frozen).execute(context)
    briefing = MorningBriefingProofAdapter(frozen).execute(context)
    assert source.calls == 1
    assert assessment.artifact_ids[0].startswith("assessment:")
    assert briefing.artifact_ids[0].startswith("briefing:sha256:")
    assert briefing.morning_briefing_available


def test_publication_validates_repositories_and_briefing_proof():
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    briefing_phase = RuntimePhaseResult(
        RuntimePhase.MORNING_BRIEFING, PhaseStatus.COMPLETED, now, now, False,
        artifact_ids=("briefing:sha256:abc",),
    )
    result = running(
        phases=(briefing_phase,), decision_id="d", training_plan_id="p",
        prescription_id="r", morning_briefing_available=True,
    )
    adapter = PublicationValidationAdapter(
        lambda value: value == "d", lambda value: value == "p", lambda value: value == "r"
    )
    assert adapter.execute(RuntimePhaseContext(result)).artifact_ids == ("d", "p", "r")
    with pytest.raises(RuntimePhaseError, match="decision_not_resolvable"):
        PublicationValidationAdapter(lambda _: False, lambda _: True, lambda _: True).execute(
            RuntimePhaseContext(result)
        )


class Clock:
    def now_utc(self):
        return datetime(2026, 8, 11, 1, tzinfo=timezone.utc)


def test_snapshot_is_persisted_before_assessment_audit_and_restored_without_recompute(tmp_path):
    repository = DuckDbAssessmentSnapshotRepository(tmp_path / "runtime.duckdb")
    source = Provider()
    provider = PersistedAssessmentSnapshotProvider(source, repository, Clock())
    context = RuntimePhaseContext(running())
    outcome = AssessmentSnapshotAdapter(provider).execute(context)
    persisted = repository.get_by_runtime_id("runtime-1")
    assert persisted is not None
    assert persisted.artifact_id == outcome.artifact_ids[0]
    assert source.calls == 1

    restarted_source = Provider()
    restarted = PersistedAssessmentSnapshotProvider(restarted_source, repository, Clock())
    repeated = AssessmentSnapshotAdapter(restarted).execute(context)
    assert repeated.artifact_ids == outcome.artifact_ids
    assert restarted_source.calls == 0


def test_decision_and_briefing_provider_restore_exact_audited_snapshot(tmp_path):
    repository = DuckDbAssessmentSnapshotRepository(tmp_path / "runtime.duckdb")
    source = Provider()
    initial = PersistedAssessmentSnapshotProvider(source, repository, Clock())
    context = RuntimePhaseContext(running())
    assessment = AssessmentSnapshotAdapter(initial).execute(context)
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    phase = RuntimePhaseResult(
        RuntimePhase.ASSESSMENT, PhaseStatus.COMPLETED, now, now, False,
        artifact_ids=assessment.artifact_ids,
    )
    resumed_context = RuntimePhaseContext(running(revision=2, phases=(phase,)))
    restarted_source = Provider()
    restarted = PersistedAssessmentSnapshotProvider(restarted_source, repository, Clock())
    restarted.bind(resumed_context)
    assert restarted.get_input() == repository.get_by_runtime_id("runtime-1").input
    proof_one = MorningBriefingProofAdapter(initial).execute(context).artifact_ids
    proof_two = MorningBriefingProofAdapter(restarted).execute(resumed_context).artifact_ids
    assert proof_one == proof_two
    assert restarted_source.calls == 0
