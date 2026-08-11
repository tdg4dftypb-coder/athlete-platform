"""Repository port and errors for operational runtime audit revisions."""
from datetime import date
from typing import Protocol, runtime_checkable

from production_runtime.models import ProductionDailyRuntimeResult


class RuntimeAuditRepositoryError(Exception):
    pass


class RuntimeAuditConflictError(RuntimeAuditRepositoryError):
    pass


class RuntimeAuditDataError(RuntimeAuditRepositoryError):
    pass


@runtime_checkable
class RuntimeAuditRepository(Protocol):
    def append(self, result: ProductionDailyRuntimeResult, expected_revision: int | None = None) -> None:
        """Append an initial attempt or its next CAS-protected immutable revision."""
        ...

    def get_by_runtime_id(self, runtime_id: str) -> ProductionDailyRuntimeResult | None:
        """Return the latest revision for one unique runtime attempt."""
        ...

    def list_for_target_date(self, target_date: date) -> tuple[ProductionDailyRuntimeResult, ...]:
        """Return latest revisions for all attempts, oldest attempt first."""
        ...

    def get_latest(self) -> ProductionDailyRuntimeResult | None:
        """Return the latest attempt revision by start time and runtime ID."""
        ...
