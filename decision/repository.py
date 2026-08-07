from typing import Protocol, runtime_checkable

from decision.history_v2 import DecisionAuditRecord


class DecisionAuditRecordRepositoryError(Exception):
    """General expected infrastructure error for Decision Audit Record Repository."""


class DecisionAuditRecordConflictError(DecisionAuditRecordRepositoryError):
    """Raised when attempting to save a record with an existing decision_id but different payload."""


class DecisionAuditRecordDataError(DecisionAuditRecordRepositoryError):
    """Raised when stored payload or metadata is corrupted, inconsistent, or unparseable."""


@runtime_checkable
class DecisionAuditRecordRepository(Protocol):
    """Repository protocol boundary for persisting and retrieving DecisionAuditRecord instances."""

    def save(self, record: DecisionAuditRecord) -> None:
        """Persists a DecisionAuditRecord append-only. Idempotent for identical payloads."""
        ...

    def get_by_id(self, decision_id: str) -> DecisionAuditRecord | None:
        """Retrieves a single DecisionAuditRecord by its decision_id."""
        ...

    def get_latest(self) -> DecisionAuditRecord | None:
        """Retrieves the latest ready DecisionAuditRecord (sorted by context.generated_at desc)."""
        ...

    def list_records(self) -> tuple[DecisionAuditRecord, ...]:
        """Lists all DecisionAuditRecord instances ordered by context.generated_at asc, decision_id asc."""
        ...
