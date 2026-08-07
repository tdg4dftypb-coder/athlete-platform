from typing import Protocol

from decision.history_v2 import DecisionAuditRecord


class DecisionAuditRecordProviderError(Exception):
    """Domain exception raised when the decision audit record data source is unavailable."""
    pass


class DecisionAuditRecordProvider(Protocol):
    """Protocol boundary for providing the latest DecisionAuditRecord."""

    def get_latest_record(self) -> DecisionAuditRecord | None:
        """Retrieves and returns the latest DecisionAuditRecord or None if no decision exists."""
        ...


class EmptyDecisionAuditRecordProvider:
    """Default provider implementation returning None (no decision available)."""

    def get_latest_record(self) -> DecisionAuditRecord | None:
        return None
