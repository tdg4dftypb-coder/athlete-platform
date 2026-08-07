from decision.history_provider import DecisionHistoryProvider, DecisionHistoryProviderError
from decision.history_v2 import DecisionHistory, DecisionHistoryBuilder
from decision.repository import (
    DecisionAuditRecordDataError,
    DecisionAuditRecordRepository,
    DecisionAuditRecordRepositoryError,
)


class RepositoryDecisionHistoryProvider(DecisionHistoryProvider):
    """Concrete DecisionHistoryProvider fetching records from DecisionAuditRecordRepository.

    Translates expected repository infrastructure and data errors into DecisionHistoryProviderError.
    """

    def __init__(
        self,
        repository: DecisionAuditRecordRepository,
        history_builder: DecisionHistoryBuilder | None = None,
    ) -> None:
        if repository is None:
            raise TypeError("repository must not be None")
        self._repository = repository
        self._history_builder = history_builder or DecisionHistoryBuilder()

    def get_history(self) -> DecisionHistory:
        try:
            records = self._repository.list_records()
            return self._history_builder.build(records)
        except (DecisionAuditRecordRepositoryError, DecisionAuditRecordDataError) as err:
            raise DecisionHistoryProviderError(
                "Decision Intelligence history is temporarily unavailable"
            ) from err
