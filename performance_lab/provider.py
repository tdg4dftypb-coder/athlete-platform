"""Performance Lab — provider boundary interface and safe default provider.

Defines the PerformanceTestSessionProvider and PerformanceTestHistoryProvider protocols,
provider exceptions, and safe empty default implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from performance_lab.domain import PerformanceTestSession
from performance_lab.history import PerformanceTestHistory


class PerformanceTestSessionProviderError(Exception):
    """Raised by a PerformanceTestSessionProvider when the underlying source fails."""


@runtime_checkable
class PerformanceTestSessionProvider(Protocol):
    """Public boundary contract for retrieving PerformanceTestSession instances."""

    def get_sessions(self) -> tuple[PerformanceTestSession, ...]:
        """Fetch test sessions.

        Raises PerformanceTestSessionProviderError on source failures.
        """
        ...


class EmptyPerformanceTestSessionProvider:
    """Safe default provider returning an empty tuple of sessions."""

    def get_sessions(self) -> tuple[PerformanceTestSession, ...]:
        return ()


class PerformanceTestHistoryProviderError(Exception):
    """Raised by a PerformanceTestHistoryProvider when the underlying source fails."""


@runtime_checkable
class PerformanceTestHistoryProvider(Protocol):
    """Public boundary contract for retrieving pre-analyzed PerformanceTestHistory instances."""

    def get_history(self) -> PerformanceTestHistory:
        """Fetch analyzed performance test history.

        Raises PerformanceTestHistoryProviderError on source failures.
        """
        ...


class EmptyPerformanceTestHistoryProvider:
    """Safe default provider returning an empty PerformanceTestHistory with no entries."""

    def get_history(self) -> PerformanceTestHistory:
        return PerformanceTestHistory(entries=())
