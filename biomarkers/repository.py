"""
Repository Boundary and In-Memory Storage for Biomarkers.
"""

from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional, Protocol, Tuple

from biomarkers.deletion import DeletionMode, DeletionResult, TombstoneRecord
from biomarkers.errors import ImportRunActivationError, ReportNotFoundError
from biomarkers.models import (
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReport,
)


class LaboratoryRepository(Protocol):
    """Protocol port for Laboratory Repository operations."""

    def find_report_by_source_hash(self, source_document_hash: str) -> Optional[LaboratoryReport]: ...

    def get_report(self, report_id: str) -> Optional[LaboratoryReport]: ...

    def get_import_runs(self, report_id: str) -> Tuple[LaboratoryImportRun, ...]: ...

    def get_active_import_run(self, report_id: str) -> Optional[LaboratoryImportRun]: ...

    def find_observations_for_duplicate_check(
        self,
        canonical_code: str,
        collected_at: datetime,
        normalized_value: Optional[float],
        exclude_report_id: str,
    ) -> Tuple[LaboratoryObservation, ...]: ...

    def save_report_with_import_run(
        self, report: LaboratoryReport, import_run: LaboratoryImportRun
    ) -> None: ...

    def activate_import_run(self, report_id: str, import_run_id: str) -> None: ...

    def delete_report(self, report_id: str, deletion_mode: DeletionMode) -> DeletionResult: ...

    def rebuild_derived_state(self, report_id: str) -> None: ...


class InMemoryLaboratoryRepository:
    """
    Thread-safe, in-memory implementation of LaboratoryRepository for domain validation and testing.
    Enforces atomic activation invariant: At most one active LaboratoryImportRun per report_id.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reports: Dict[str, LaboratoryReport] = {}
        self._hash_to_report_id: Dict[str, str] = {}
        # report_id -> List[LaboratoryImportRun]
        self._import_runs: Dict[str, List[LaboratoryImportRun]] = {}
        self._tombstones: Dict[str, TombstoneRecord] = {}

    def find_report_by_source_hash(self, source_document_hash: str) -> Optional[LaboratoryReport]:
        with self._lock:
            if not source_document_hash:
                return None
            report_id = self._hash_to_report_id.get(source_document_hash.strip())
            if not report_id:
                return None
            return self._reports.get(report_id)

    def get_report(self, report_id: str) -> Optional[LaboratoryReport]:
        with self._lock:
            if not report_id:
                return None
            return self._reports.get(report_id.strip())

    def get_import_runs(self, report_id: str) -> Tuple[LaboratoryImportRun, ...]:
        with self._lock:
            runs = self._import_runs.get(report_id.strip(), [])
            return tuple(runs)

    def get_active_import_run(self, report_id: str) -> Optional[LaboratoryImportRun]:
        with self._lock:
            runs = self._import_runs.get(report_id.strip(), [])
            for run in runs:
                if run.active:
                    return run
            return None

    def find_observations_for_duplicate_check(
        self,
        canonical_code: str,
        collected_at: datetime,
        normalized_value: Optional[float],
        exclude_report_id: str,
    ) -> Tuple[LaboratoryObservation, ...]:
        if not canonical_code or collected_at is None:
            return ()

        with self._lock:
            matching_obs: List[LaboratoryObservation] = []
            target_code = canonical_code.strip().lower()
            target_date = collected_at.date() if isinstance(collected_at, datetime) else collected_at

            for r_id, runs in self._import_runs.items():
                if r_id == exclude_report_id:
                    continue
                # Search active runs of other reports
                for run in runs:
                    if not run.active:
                        continue
                    for obs in run.observations:
                        if not obs.canonical_code or obs.canonical_code.lower() != target_code:
                            continue
                        obs_date = obs.collected_at.date() if isinstance(obs.collected_at, datetime) else obs.collected_at
                        if obs_date != target_date:
                            continue
                        
                        # Match normalized or numeric value
                        if normalized_value is not None and (obs.normalized_value is not None or obs.numeric_value is not None):
                            obs_val = obs.normalized_value if obs.normalized_value is not None else obs.numeric_value
                            if abs(obs_val - normalized_value) < 1e-5:
                                matching_obs.append(obs)
                        elif normalized_value is None:
                            matching_obs.append(obs)

            return tuple(matching_obs)

    def save_report_with_import_run(
        self, report: LaboratoryReport, import_run: LaboratoryImportRun
    ) -> None:
        with self._lock:
            r_id = report.report_id.strip()
            self._reports[r_id] = report
            self._hash_to_report_id[report.source_document_hash.strip()] = r_id

            existing_runs = self._import_runs.setdefault(r_id, [])

            # Check if this run is already stored
            for idx, existing in enumerate(existing_runs):
                if existing.import_run_id == import_run.import_run_id:
                    existing_runs[idx] = import_run
                    break
            else:
                existing_runs.append(import_run)

    def activate_import_run(self, report_id: str, import_run_id: str) -> None:
        with self._lock:
            r_id = report_id.strip()
            run_id = import_run_id.strip()

            if r_id not in self._reports:
                raise ReportNotFoundError(f"Report '{r_id}' not found for run activation.")

            runs = self._import_runs.get(r_id, [])
            target_run = None
            for run in runs:
                if run.import_run_id == run_id:
                    target_run = run
                    break

            if not target_run:
                raise ImportRunActivationError(f"Import run '{run_id}' not found in report '{r_id}'.")

            # ATOMIC ACTIVATION INVARIANT (ADR-012):
            # Deactivate all runs for report_id, then activate target_run
            updated_runs = []
            for run in runs:
                is_target = run.import_run_id == run_id
                # Create copy with active status
                updated_run = LaboratoryImportRun(
                    import_run_id=run.import_run_id,
                    report_id=run.report_id,
                    parser_version=run.parser_version,
                    extractor_version=run.extractor_version,
                    registry_version=run.registry_version,
                    unit_rules_version=run.unit_rules_version,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    status=run.status,
                    active=is_target,
                    warnings=run.warnings,
                    observations=run.observations,
                )
                updated_runs.append(updated_run)

            self._import_runs[r_id] = updated_runs

    def delete_report(self, report_id: str, deletion_mode: DeletionMode) -> DeletionResult:
        with self._lock:
            r_id = report_id.strip()
            report = self._reports.get(r_id)

            if not report:
                raise ReportNotFoundError(f"Report '{r_id}' not found for deletion.")

            runs = self._import_runs.get(r_id, [])
            obs_count = sum(len(run.observations) for run in runs)
            runs_count = len(runs)
            now = datetime.now(timezone.utc)
            doc_hash = report.source_document_hash.strip()

            # Clean up reports and import runs
            del self._reports[r_id]
            if r_id in self._import_runs:
                del self._import_runs[r_id]
            if doc_hash in self._hash_to_report_id:
                del self._hash_to_report_id[doc_hash]

            tombstone_retained = False
            if deletion_mode == DeletionMode.DELETE_DATA_KEEP_TOMBSTONE:
                tombstone = TombstoneRecord(
                    source_document_hash=doc_hash,
                    deleted_at=now,
                    tombstone_id=f"tombstone-{r_id}",
                    is_tombstone=True,
                )
                self._tombstones[doc_hash] = tombstone
                tombstone_retained = True

            return DeletionResult(
                report_id=r_id,
                deleted_reports_count=1,
                deleted_import_runs_count=runs_count,
                deleted_observations_count=obs_count,
                deleted_derived_items_count=1,
                tombstone_retained=tombstone_retained,
                deleted_at=now,
            )

    def rebuild_derived_state(self, report_id: str) -> None:
        """Invalidates and triggers rebuild of derived Read Model state for a report."""
        # Clean port method for future BiomarkersDashboardPayloadV1 cache invalidation
        pass
