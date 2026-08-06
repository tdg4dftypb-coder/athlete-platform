"""Performance Lab — provider boundary interface and safe default provider.

Defines the PerformanceTestSessionProvider protocol, provider exception,
and safe empty default implementation.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from performance_lab.domain import PerformanceTestSession


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
