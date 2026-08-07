from typing import Protocol, runtime_checkable

from decision.history_v2 import DecisionHistory


class DecisionHistoryProviderError(Exception):
    """Domain exception raised when the decision history data source is unavailable."""
    pass


@runtime_checkable
class DecisionHistoryProvider(Protocol):
    """Protocol boundary for providing the complete DecisionHistory read model."""

    def get_history(self) -> DecisionHistory:
        """Retrieves and returns the complete DecisionHistory."""
        ...


class EmptyDecisionHistoryProvider:
    """Default provider implementation returning an empty DecisionHistory read model."""

    def get_history(self) -> DecisionHistory:
        return DecisionHistory(records=())
