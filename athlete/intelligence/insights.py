from athlete.intelligence.models import (
    AthleteInsight,
    AthleteObservation,
)
from athlete.intelligence.rules import ComplianceRule, FatigueRule, RecoveryRule
from athlete.memory.models import WorkoutMemoryObservation


class InsightBuilder:
    """Projects the currently supported observation groups into typed insights."""

    _RULES = (
        FatigueRule(),
        RecoveryRule(),
        ComplianceRule(),
    )

    def build(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...] = (),
    ) -> tuple[AthleteInsight, ...]:
        return tuple(
            insight
            for rule in self._RULES
            if (
                insight := rule.evaluate(
                    observations,
                    workout_history,
                )
            )
            is not None
        )
