"""Small bounded adapters shared by the authoritative daily coordinator."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable

from morning_briefing.builder import MorningBriefingBuilder
from morning_briefing.provider import MorningBriefingInputProvider
from morning_briefing.serialization import MorningBriefingSerializer
from production_runtime.assessment_snapshot import (
    AssessmentSnapshot,
    AssessmentSnapshotCodec,
    AssessmentSnapshotConflictError,
    AssessmentSnapshotIntegrityError,
    AssessmentSnapshotMissingError,
    AssessmentSnapshotRepository,
    AssessmentSnapshotUnavailableError,
)
from production_runtime.coordinator import (
    RECONCILIATION_NOT_APPLICABLE,
    RuntimePhaseContext,
    RuntimePhaseError,
    RuntimePhaseOutcome,
)
from production_runtime.ingestion_slice import IngestionRuntimeSlice
from production_runtime.models import PhaseStatus, RuntimeWarning


class CallablePhaseAdapter:
    """Turns an existing application service function into a phase port."""

    def __init__(self, function: Callable[[RuntimePhaseContext], RuntimePhaseOutcome]) -> None:
        self._function = function

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        return self._function(context)


class ReconciliationPolicySkipAdapter:
    """Truthful policy skip while factual-activity completion matching is absent."""

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        return RuntimePhaseOutcome(
            status=PhaseStatus.SKIPPED,
            warning_codes=(RECONCILIATION_NOT_APPLICABLE,),
            warnings=(RuntimeWarning(
                RECONCILIATION_NOT_APPLICABLE,
                "ACTIVITY_RECORDED is not interpreted as WORKOUT_COMPLETED",
                "reconciliation",
            ),),
            reconciliations_created=0,
        )


class FrozenMorningBriefingInputProvider:
    """Caches one immutable provider result for all consumers in one attempt."""

    def __init__(self, delegate: MorningBriefingInputProvider) -> None:
        self._delegate = delegate
        self._value = None

    def get_input(self):
        if self._value is None:
            self._value = self._delegate.get_input()
        return self._value


class PersistedAssessmentSnapshotProvider:
    """Attempt-bound provider that computes once or restores exact persisted input."""

    def __init__(self, delegate, repository: AssessmentSnapshotRepository, clock) -> None:
        self._delegate = delegate
        self._repository = repository
        self._clock = clock
        self._context = None
        self._snapshot = None

    def bind(self, context: RuntimePhaseContext) -> None:
        if self._context is not None and self._context.result.runtime_id != context.result.runtime_id:
            self._snapshot = None
        self._context = context
        try:
            existing = self._repository.get_by_runtime_id(context.result.runtime_id)
            assessment = next(
                (p for p in context.result.phases if p.phase.value == "assessment"), None
            )
            if assessment is not None:
                if len(assessment.artifact_ids) != 1:
                    raise AssessmentSnapshotIntegrityError("assessment audit reference is malformed")
                if existing is None:
                    raise AssessmentSnapshotMissingError("assessment snapshot is missing")
                if existing.artifact_id != assessment.artifact_ids[0]:
                    raise AssessmentSnapshotIntegrityError("assessment audit artifact mismatch")
            if existing is not None:
                if existing.target_local_date != context.target_local_date:
                    raise AssessmentSnapshotIntegrityError("assessment snapshot target date mismatch")
                self._snapshot = existing
        except Exception as error:
            self._translate(error)

    def get_snapshot(self) -> AssessmentSnapshot:
        if self._context is None:
            raise RuntimePhaseError("assessment_snapshot_unavailable", "provider is not attempt-bound")
        if self._snapshot is not None:
            return self._snapshot
        try:
            value = self._delegate.get_input()
            snapshot = AssessmentSnapshot(
                runtime_id=self._context.result.runtime_id,
                target_local_date=self._context.target_local_date,
                created_at_utc=self._clock.now_utc(),
                input=value,
                artifact_id=AssessmentSnapshotCodec.artifact_id_for(value),
            )
            self._repository.save(snapshot)
            self._snapshot = snapshot
            return snapshot
        except Exception as error:
            self._translate(error)

    def get_input(self):
        return self.get_snapshot().input

    @staticmethod
    def _translate(error):
        if isinstance(error, RuntimePhaseError):
            raise error
        if isinstance(error, AssessmentSnapshotMissingError):
            raise RuntimePhaseError("assessment_snapshot_missing", str(error)) from error
        if isinstance(error, AssessmentSnapshotConflictError):
            raise RuntimePhaseError("assessment_snapshot_conflict", str(error)) from error
        if isinstance(error, AssessmentSnapshotIntegrityError):
            raise RuntimePhaseError("assessment_snapshot_corrupt", str(error)) from error
        if isinstance(error, AssessmentSnapshotUnavailableError):
            raise RuntimePhaseError("assessment_snapshot_unavailable", str(error)) from error
        raise error


class AssessmentSnapshotAdapter:
    """Freezes the canonical Morning Coach projection without persisting coaching state."""

    def __init__(self, provider) -> None:
        self._provider = provider

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        if hasattr(self._provider, "bind"):
            self._provider.bind(context)
            snapshot = self._provider.get_snapshot()
            return RuntimePhaseOutcome(artifact_ids=(snapshot.artifact_id,))
        snapshot = self._provider.get_input()
        snapshot_id = f"assessment:{sha256(snapshot.generated_at.isoformat().encode()).hexdigest()}"
        return RuntimePhaseOutcome(artifact_ids=(snapshot_id,))


class MorningBriefingProofAdapter:
    """Builds existing athlete-facing content and records its canonical content digest."""

    def __init__(self, provider: FrozenMorningBriefingInputProvider) -> None:
        self._provider = provider
        self._builder = MorningBriefingBuilder()
        self._serializer = MorningBriefingSerializer()

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        if hasattr(self._provider, "bind"):
            self._provider.bind(context)
        briefing = self._builder.build(self._provider.get_input())
        payload = json.dumps(
            self._serializer.serialize(briefing), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        artifact_id = f"briefing:sha256:{sha256(payload).hexdigest()}"
        return RuntimePhaseOutcome(
            artifact_ids=(artifact_id,),
            morning_briefing_available=True,
        )


class PublicationValidationAdapter:
    """Read/check-only validation of references produced by earlier phases."""

    def __init__(
        self,
        decision_exists: Callable[[str], bool],
        plan_exists: Callable[[str], bool],
        prescription_exists: Callable[[str], bool],
        assessment_resolves: Callable[[str, str, object], bool] | None = None,
        reconciliation_exists: Callable[[str], bool] | None = None,
        adaptation_resolves: Callable[[object], bool] | None = None,
    ) -> None:
        self._decision_exists = decision_exists
        self._plan_exists = plan_exists
        self._prescription_exists = prescription_exists
        self._assessment_resolves = assessment_resolves
        self._reconciliation_exists = reconciliation_exists
        self._adaptation_resolves = adaptation_resolves

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        result = context.result
        if self._adaptation_resolves is not None:
            phases = [p for p in result.phases if p.phase.value == "plan_adaptation"]
            if len(phases) != 1 or not self._adaptation_resolves(phases[0]):
                raise RuntimePhaseError("plan_adaptation_not_resolvable")
        if self._reconciliation_exists is not None:
            reconciliation_phases = [
                phase for phase in result.phases
                if phase.phase.value == "reconciliation"
            ]
            if not reconciliation_phases:
                raise RuntimePhaseError("reconciliation_not_resolvable")
            reconciliation_phase = reconciliation_phases[0]
            if reconciliation_phase.status is PhaseStatus.COMPLETED:
                if len(reconciliation_phase.artifact_ids) != 1:
                    raise RuntimePhaseError("reconciliation_not_resolvable")
                if not self._reconciliation_exists(
                    reconciliation_phase.artifact_ids[0]
                ):
                    raise RuntimePhaseError("reconciliation_not_resolvable")
            elif reconciliation_phase.status is PhaseStatus.SKIPPED:
                if reconciliation_phase.artifact_ids:
                    raise RuntimePhaseError("reconciliation_not_resolvable")
        if self._assessment_resolves is not None:
            assessment_phases = [p for p in result.phases if p.phase.value == "assessment"]
            if not assessment_phases or len(assessment_phases[0].artifact_ids) != 1:
                raise RuntimePhaseError("assessment_snapshot_missing")
            assessment_id = assessment_phases[0].artifact_ids[0]
            if not self._assessment_resolves(
                result.runtime_id, assessment_id, result.target_local_date
            ):
                raise RuntimePhaseError("assessment_snapshot_corrupt")
        checks = (
            (result.decision_id, self._decision_exists, "decision_not_resolvable"),
            (result.training_plan_id, self._plan_exists, "training_plan_not_resolvable"),
            (result.prescription_id, self._prescription_exists, "prescription_not_resolvable"),
        )
        for artifact_id, exists, code in checks:
            if artifact_id is None or not exists(artifact_id):
                raise RuntimePhaseError(code)
        if not result.morning_briefing_available:
            raise RuntimePhaseError("briefing_not_resolvable")
        briefing_phases = [p for p in result.phases if p.phase.value == "morning_briefing"]
        if not briefing_phases or not briefing_phases[0].artifact_ids:
            raise RuntimePhaseError("briefing_not_resolvable")
        return RuntimePhaseOutcome(artifact_ids=tuple(
            item for item in (result.decision_id, result.training_plan_id, result.prescription_id)
            if item is not None
        ))


@dataclass
class IngestionRuntimePhaseAdapters:
    """Runs 27.3 services inside the parent audit chain, caching only in-process output."""

    runtime_slice: IngestionRuntimeSlice
    _ingestion_outcome: object | None = None

    def ingestion(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        outcome = self.runtime_slice.execute_ingestion()
        self._ingestion_outcome = outcome
        if outcome.failure is not None:
            raise RuntimePhaseError(outcome.failure.code, outcome.failure.detail)
        return RuntimePhaseOutcome(
            status=outcome.phase.status,
            changed_state=outcome.phase.changed_state,
            item_count=outcome.phase.item_count,
            artifact_ids=outcome.phase.artifact_ids,
            warning_codes=outcome.phase.warning_codes,
            warnings=outcome.warnings,
            source_watermarks=(outcome.watermark,),
            activities_discovered=outcome.discovered,
        )

    def facts(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        source_dir = self.runtime_slice.source_directory
        ingestion_phase = next(p for p in context.result.phases if p.phase.value == "ingestion")
        artifacts = tuple(source_dir / item for item in ingestion_phase.artifact_ids)
        outcome = self.runtime_slice.execute_fact_synchronization(artifacts)
        if outcome.failure is not None:
            raise RuntimePhaseError(outcome.failure.code, outcome.failure.detail)
        return RuntimePhaseOutcome(
            status=outcome.phase.status,
            changed_state=outcome.phase.changed_state,
            item_count=outcome.phase.item_count,
            artifact_ids=outcome.phase.artifact_ids,
            warning_codes=outcome.phase.warning_codes,
            warnings=outcome.warnings,
            source_watermarks=(outcome.watermark,) if outcome.watermark else (),
            activity_facts_created=outcome.created,
            activities_already_present=outcome.already_present,
        )
