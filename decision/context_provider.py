from datetime import datetime
from typing import Protocol

from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    ContextDataStatus,
    PerformanceDecisionContext,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from decision.context_builder import AthleteDecisionContextBuilder


class AthleteDecisionContextProvider(Protocol):
    """Protocol boundary for providing an AthleteDecisionContext."""

    def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
        """Builds and returns the AthleteDecisionContext for the given timestamp."""
        ...


class EmptyAthleteDecisionContextProvider:
    """Default provider implementation returning UNAVAILABLE status for all domain contexts."""

    def __init__(self, builder: AthleteDecisionContextBuilder | None = None) -> None:
        self._builder = builder or AthleteDecisionContextBuilder()

    def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be a datetime instance")

        return self._builder.build(
            generated_at=generated_at,
            recovery=RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE),
            training=TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE),
            biomarkers=BiomarkerDecisionContext(
                status=ContextDataStatus.UNAVAILABLE,
                attention_count=0,
                critical_count=0,
                signals=(),
            ),
            performance=PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE),
        )
