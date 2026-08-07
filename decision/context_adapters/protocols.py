from datetime import datetime
from typing import Protocol, runtime_checkable

from decision.context import (
    BiomarkerDecisionContext,
    PerformanceDecisionContext,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


@runtime_checkable
class RecoveryDecisionContextAdapter(Protocol):
    """Protocol boundary for providing a RecoveryDecisionContext."""

    def get_context(self, generated_at: datetime) -> RecoveryDecisionContext:
        ...


@runtime_checkable
class TrainingDecisionContextAdapter(Protocol):
    """Protocol boundary for providing a TrainingDecisionContext."""

    def get_context(self, generated_at: datetime) -> TrainingDecisionContext:
        ...


@runtime_checkable
class BiomarkerDecisionContextAdapter(Protocol):
    """Protocol boundary for providing a BiomarkerDecisionContext."""

    def get_context(self, generated_at: datetime) -> BiomarkerDecisionContext:
        ...


@runtime_checkable
class PerformanceDecisionContextAdapter(Protocol):
    """Protocol boundary for providing a PerformanceDecisionContext."""

    def get_context(self, generated_at: datetime) -> PerformanceDecisionContext:
        ...
