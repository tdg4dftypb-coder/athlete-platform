"""Small bounded adapters shared by the authoritative daily coordinator."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable

from morning_briefing.builder import MorningBriefingBuilder
from morning_briefing.provider import MorningBriefingInputProvider
from morning_briefing.serialization import MorningBriefingSerializer
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


class AssessmentSnapshotAdapter:
    """Freezes the canonical Morning Coach projection without persisting coaching state."""

    def __init__(self, provider: FrozenMorningBriefingInputProvider) -> None:
        self._provider = provider

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
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
    ) -> None:
        self._decision_exists = decision_exists
        self._plan_exists = plan_exists
        self._prescription_exists = prescription_exists

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        result = context.result
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
