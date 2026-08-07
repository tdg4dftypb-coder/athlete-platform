from decision.audit_provider import DecisionAuditRecordProvider, DecisionAuditRecordProviderError
from decision.history_v2 import DecisionAuditRecord
from decision.repository import (
    DecisionAuditRecordDataError,
    DecisionAuditRecordRepository,
    DecisionAuditRecordRepositoryError,
)


class RepositoryDecisionAuditRecordProvider(DecisionAuditRecordProvider):
    """Concrete DecisionAuditRecordProvider fetching the latest record from DecisionAuditRecordRepository.

    Translates expected repository infrastructure and data errors into DecisionAuditRecordProviderError.
    """

    def __init__(self, repository: DecisionAuditRecordRepository) -> None:
        if repository is None:
            raise TypeError("repository must not be None")
        self._repository = repository

    def get_latest_record(self) -> DecisionAuditRecord | None:
        try:
            return self._repository.get_latest()
        except (DecisionAuditRecordRepositoryError, DecisionAuditRecordDataError) as err:
            raise DecisionAuditRecordProviderError(
                "Decision Intelligence repository is temporarily unavailable"
            ) from err
