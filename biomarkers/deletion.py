"""
Deletion Semantics and Privacy-Safe Document Retention.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
from typing import Dict, Optional, Protocol

from biomarkers.errors import LaboratoryDeletionError


class DeletionMode(Enum):
    DELETE_DATA_KEEP_TOMBSTONE = "delete_data_keep_tombstone"
    DELETE_EVERYTHING = "delete_everything"


@dataclass(frozen=True)
class TombstoneRecord:
    """
    Immutable tombstone record for right-to-erasure compliance.
    STRICT PRIVACY POLICY:
    Must contain ZERO health metrics, ZERO raw observation values/names, and ZERO file names.
    """

    source_document_hash: Optional[str]
    deleted_at: datetime
    tombstone_id: str
    is_tombstone: bool = True


@dataclass(frozen=True)
class DeletionResult:
    """Immutable report of a laboratory report deletion operation."""

    report_id: str
    deleted_reports_count: int
    deleted_import_runs_count: int
    deleted_observations_count: int
    deleted_derived_items_count: int
    tombstone_retained: bool
    deleted_at: datetime


class SourceDocumentStore(Protocol):
    """Protocol port for binary source document file storage."""

    def delete(self, source_document_hash: str) -> bool: ...

    def save(self, source_document_hash: str, content: bytes) -> None: ...

    def exists(self, source_document_hash: str) -> bool: ...


class InMemorySourceDocumentStore:
    """In-memory implementation of SourceDocumentStore for testing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, bytes] = {}

    def save(self, source_document_hash: str, content: bytes) -> None:
        if not source_document_hash or not content:
            return
        with self._lock:
            self._store[source_document_hash.strip()] = content

    def exists(self, source_document_hash: str) -> bool:
        if not source_document_hash:
            return False
        with self._lock:
            return source_document_hash.strip() in self._store

    def delete(self, source_document_hash: str) -> bool:
        if not source_document_hash:
            return False
        with self._lock:
            h = source_document_hash.strip()
            if h in self._store:
                del self._store[h]
                return True
            return False


class LaboratoryDeletionService:
    """
    Orchestrates privacy-safe atomic deletion of laboratory reports, import runs,
    observations, binary document files, and derived read model states.
    """

    def __init__(self, repository: Any, document_store: SourceDocumentStore) -> None:
        self.repository = repository
        self.document_store = document_store

    def delete(self, report_id: str, deletion_mode: DeletionMode = DeletionMode.DELETE_DATA_KEEP_TOMBSTONE) -> DeletionResult:
        if not report_id or not report_id.strip():
            raise LaboratoryDeletionError("report_id cannot be empty for deletion.")

        r_id = report_id.strip()
        report = self.repository.get_report(r_id)
        if not report:
            raise LaboratoryDeletionError(f"Report '{r_id}' not found for deletion.")

        doc_hash = report.source_document_hash

        # 1. Invalidate & rebuild derived Read Model state
        self.repository.rebuild_derived_state(r_id)

        # 2. Delete report, import runs & observations from repository
        result = self.repository.delete_report(r_id, deletion_mode)

        # 3. Delete binary document file from store
        if doc_hash:
            self.document_store.delete(doc_hash)

        return result
