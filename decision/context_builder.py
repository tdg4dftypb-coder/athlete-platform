from datetime import datetime

from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    PerformanceDecisionContext,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


class AthleteDecisionContextBuilder:
    """Combines four ready domain decision context snapshots into an immutable AthleteDecisionContext."""

    def build(
        self,
        generated_at: datetime,
        recovery: RecoveryDecisionContext,
        training: TrainingDecisionContext,
        biomarkers: BiomarkerDecisionContext,
        performance: PerformanceDecisionContext,
    ) -> AthleteDecisionContext:
        """Constructs an immutable AthleteDecisionContext with explicit timestamp."""
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be a datetime instance")

        return AthleteDecisionContext(
            generated_at=generated_at,
            recovery=recovery,
            training=training,
            biomarkers=biomarkers,
            performance=performance,
        )
