"""Audited Stage 27.3 runtime slice for FIT ingestion and activity facts only."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable
from uuid import uuid4

import duckdb

from application.standard_fit_ingestion import (
    MissingPersistedWorkoutError,
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from production_runtime.clock import RuntimeClock, SystemUtcRuntimeClock
from production_runtime.coordinator import RuntimeAttemptNotResumableError
from production_runtime.models import (
    RUNTIME_CONTRACT_VERSION,
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
    logical_execution_key,
)
from production_runtime.repository import RuntimeAuditRepository


SOURCE_UNAVAILABLE = "source_unavailable"
INVALID_ACTIVITY_ARTIFACT = "invalid_activity_artifact"
PERSISTENCE_UNAVAILABLE = "persistence_unavailable"
PHASE_INTERRUPTED = "phase_interrupted"


class FitSourceUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class FitSourceSnapshot:
    artifacts: tuple[Path, ...]
    watermark: SourceWatermark


@dataclass(frozen=True)
class _IngestionOutcome:
    phase: RuntimePhaseResult
    successful_artifacts: tuple[Path, ...]
    discovered: int
    warnings: tuple[RuntimeWarning, ...]
    failure: RuntimeFailure | None
    watermark: SourceWatermark


@dataclass(frozen=True)
class _SynchronizationOutcome:
    phase: RuntimePhaseResult
    created: int
    already_present: int
    warnings: tuple[RuntimeWarning, ...]
    failure: RuntimeFailure | None
    watermark: SourceWatermark | None


class FitArtifactDiscovery:
    def __init__(self, source_directory: Path) -> None:
        self._source_directory = source_directory

    @property
    def source_directory(self) -> Path:
        return self._source_directory

    def discover(self, observed_at_utc: datetime) -> FitSourceSnapshot:
        if not self._source_directory.is_dir():
            raise FitSourceUnavailableError(
                f"FIT source directory is unavailable: {self._source_directory}"
            )
        artifacts = tuple(sorted(
            (path for path in self._source_directory.glob("*.fit") if path.is_file()),
            key=lambda path: path.name,
        ))
        digest = sha256()
        for path in artifacts:
            stat = path.stat()
            digest.update(f"{path.name}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
        return FitSourceSnapshot(
            artifacts=artifacts,
            watermark=SourceWatermark(
                source="fit_directory",
                kind="directory_snapshot_sha256",
                value=f"sha256:{digest.hexdigest()}",
                observed_at_utc=observed_at_utc,
            ),
        )


class IngestionRuntimeSlice:
    """Runs only INGESTION and ACTIVITY_FACT_SYNCHRONIZATION with audit revisions."""

    def __init__(
        self,
        audit_repository: RuntimeAuditRepository,
        discovery: FitArtifactDiscovery,
        ingestion: StandardFitWorkoutIngestionService,
        fact_synchronization: StandardActivityFactSynchronizationService,
        clock: RuntimeClock | None = None,
        runtime_id_factory: Callable[[], str] | None = None,
        timezone_name: str = "Europe/Warsaw",
    ) -> None:
        self._audit = audit_repository
        self._discovery = discovery
        self._ingestion = ingestion
        self._fact_synchronization = fact_synchronization
        self._clock = clock or SystemUtcRuntimeClock()
        self._runtime_id_factory = runtime_id_factory or (lambda: f"runtime-{uuid4()}")
        self._timezone_name = timezone_name

    def run_new_attempt(self, target_local_date: date) -> ProductionDailyRuntimeResult:
        if type(target_local_date) is not date:
            raise TypeError("target_local_date must be a date")
        started_at = self._clock.now_utc()
        initial = ProductionDailyRuntimeResult(
            runtime_id=self._runtime_id_factory(),
            logical_execution_key=logical_execution_key(target_local_date),
            revision=1,
            contract_version=RUNTIME_CONTRACT_VERSION,
            target_local_date=target_local_date,
            timezone_name=self._timezone_name,
            started_at_utc=started_at,
            completed_at_utc=None,
            status=RuntimeStatus.RUNNING,
        )
        self._audit.append(initial)
        return self._continue(initial)

    def resume_attempt(self, runtime_id: str) -> ProductionDailyRuntimeResult:
        current = self._audit.get_by_runtime_id(runtime_id)
        if current is None:
            raise ValueError(f"Unknown runtime_id '{runtime_id}'")
        if current.status is not RuntimeStatus.RUNNING:
            raise RuntimeAttemptNotResumableError(
                f"Runtime attempt '{runtime_id}' is terminal with status {current.status.value}"
            )
        return self._continue(current)

    def _continue(self, current: ProductionDailyRuntimeResult) -> ProductionDailyRuntimeResult:
        ingestion_phase = next(
            (item for item in current.phases if item.phase is RuntimePhase.INGESTION),
            None,
        )
        if ingestion_phase is None:
            try:
                ingestion_outcome = self._execute_ingestion()
            except Exception as error:
                return self._terminate_from_exception(current, RuntimePhase.INGESTION, error)
            current = replace(
                current,
                revision=current.revision + 1,
                phases=current.phases + (ingestion_outcome.phase,),
                activities_discovered=ingestion_outcome.discovered,
                source_watermarks=current.source_watermarks + (ingestion_outcome.watermark,),
                warnings=current.warnings + ingestion_outcome.warnings,
            )
            self._audit.append(current, expected_revision=current.revision - 1)
            artifacts = ingestion_outcome.successful_artifacts
            ingestion_failure = ingestion_outcome.failure
        else:
            artifacts = tuple(
                self._discovery.source_directory / artifact_id
                for artifact_id in ingestion_phase.artifact_ids
            )
            ingestion_failure = (
                RuntimeFailure(INVALID_ACTIVITY_ARTIFACT, RuntimePhase.INGESTION)
                if ingestion_phase.status is PhaseStatus.FAILED else None
            )

        try:
            synchronization = self._execute_fact_synchronization(artifacts)
        except Exception as error:
            return self._terminate_from_exception(
                current,
                RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
                error,
                partial=True,
            )

        warnings = current.warnings + synchronization.warnings
        failure = synchronization.failure or ingestion_failure
        watermarks = current.source_watermarks
        if synchronization.watermark is not None:
            watermarks += (synchronization.watermark,)
        terminal = replace(
            current,
            revision=current.revision + 1,
            completed_at_utc=self._clock.now_utc(),
            status=RuntimeStatus.PARTIAL,
            phases=current.phases + (synchronization.phase,),
            activity_facts_created=synchronization.created,
            activities_already_present=synchronization.already_present,
            source_watermarks=watermarks,
            warnings=warnings,
            failure=failure,
        )
        self._audit.append(terminal, expected_revision=current.revision)
        return terminal

    @property
    def source_directory(self) -> Path:
        return self._discovery.source_directory

    def execute_ingestion(self) -> _IngestionOutcome:
        started_at = self._clock.now_utc()
        snapshot = self._discovery.discover(started_at)
        persisted = 0
        successful = []
        warning_records = []
        for artifact in snapshot.artifacts:
            try:
                result = self._ingestion.ingest(artifact)
                successful.append(artifact)
                persisted += int(result.persisted)
            except duckdb.Error:
                raise
            except Exception as error:
                warning_records.append(RuntimeWarning(
                    INVALID_ACTIVITY_ARTIFACT,
                    self._bounded_detail(error),
                    artifact.name,
                ))
        failed = bool(warning_records)
        phase = RuntimePhaseResult(
            phase=RuntimePhase.INGESTION,
            status=PhaseStatus.FAILED if failed else PhaseStatus.COMPLETED,
            started_at_utc=started_at,
            completed_at_utc=self._clock.now_utc(),
            changed_state=persisted > 0,
            item_count=persisted,
            artifact_ids=tuple(path.name for path in successful),
            warning_codes=(INVALID_ACTIVITY_ARTIFACT,) if failed else (),
        )
        return _IngestionOutcome(
            phase=phase,
            successful_artifacts=tuple(successful),
            discovered=len(snapshot.artifacts),
            warnings=tuple(warning_records),
            failure=(
                RuntimeFailure(INVALID_ACTIVITY_ARTIFACT, RuntimePhase.INGESTION)
                if failed else None
            ),
            watermark=snapshot.watermark,
        )

    def _execute_ingestion(self) -> _IngestionOutcome:
        """Backward-compatible override point retained for the 27.3 slice."""
        return self.execute_ingestion()

    def execute_fact_synchronization(
        self,
        artifacts: tuple[Path, ...],
    ) -> _SynchronizationOutcome:
        started_at = self._clock.now_utc()
        created = 0
        existing = 0
        artifact_ids = []
        seen_artifact_ids = set()
        source_keys = set()
        warning_records = []
        for artifact in artifacts:
            try:
                result = self._fact_synchronization.synchronize(artifact)
                created += int(result.created)
                existing += int(not result.created)
                if result.event_id not in seen_artifact_ids:
                    seen_artifact_ids.add(result.event_id)
                    artifact_ids.append(result.event_id)
                source_keys.add(f"{result.source_type}:{result.source_key}")
            except duckdb.Error:
                raise
            except (MissingPersistedWorkoutError, OSError) as error:
                warning_records.append(RuntimeWarning(
                    PHASE_INTERRUPTED,
                    self._bounded_detail(error),
                    artifact.name,
                ))
            except Exception:
                raise
        failed = bool(warning_records)
        watermark = None
        if source_keys or not artifacts:
            digest = sha256("\n".join(sorted(source_keys)).encode("utf-8")).hexdigest()
            watermark = SourceWatermark(
                source="activity_facts",
                kind="fit_source_identity_set_sha256",
                value=f"sha256:{digest}",
                observed_at_utc=self._clock.now_utc(),
            )
        phase = RuntimePhaseResult(
            phase=RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
            status=PhaseStatus.FAILED if failed else PhaseStatus.COMPLETED,
            started_at_utc=started_at,
            completed_at_utc=self._clock.now_utc(),
            changed_state=created > 0,
            item_count=created + existing,
            artifact_ids=tuple(artifact_ids),
            warning_codes=(PHASE_INTERRUPTED,) if failed else (),
        )
        return _SynchronizationOutcome(
            phase=phase,
            created=created,
            already_present=existing,
            warnings=tuple(warning_records),
            failure=(
                RuntimeFailure(PHASE_INTERRUPTED, RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION)
                if failed else None
            ),
            watermark=watermark,
        )

    def _execute_fact_synchronization(
        self,
        artifacts: tuple[Path, ...],
    ) -> _SynchronizationOutcome:
        """Backward-compatible override point retained for the 27.3 slice."""
        return self.execute_fact_synchronization(artifacts)

    def _terminate_from_exception(
        self,
        current: ProductionDailyRuntimeResult,
        phase: RuntimePhase,
        error: Exception,
        partial: bool = False,
    ) -> ProductionDailyRuntimeResult:
        code = self._failure_code(error)
        now = self._clock.now_utc()
        failed_phase = RuntimePhaseResult(
            phase=phase,
            status=PhaseStatus.FAILED,
            started_at_utc=now,
            completed_at_utc=now,
            changed_state=False,
            warning_codes=(code,),
        )
        terminal = replace(
            current,
            revision=current.revision + 1,
            completed_at_utc=now,
            status=RuntimeStatus.PARTIAL if partial or current.phases else RuntimeStatus.FAILED,
            phases=current.phases + (failed_phase,),
            warnings=current.warnings + (RuntimeWarning(code, self._bounded_detail(error), phase.value),),
            failure=RuntimeFailure(code, phase, self._bounded_detail(error)),
        )
        self._audit.append(terminal, expected_revision=current.revision)
        return terminal

    @staticmethod
    def _failure_code(error: Exception) -> str:
        if isinstance(error, FitSourceUnavailableError):
            return SOURCE_UNAVAILABLE
        if isinstance(error, duckdb.Error):
            return PERSISTENCE_UNAVAILABLE
        return PHASE_INTERRUPTED

    @staticmethod
    def _bounded_detail(error: Exception) -> str:
        detail = f"{type(error).__name__}: {error}".strip()
        return detail[:200] or type(error).__name__
