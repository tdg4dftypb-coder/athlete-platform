from datetime import datetime

from athlete.intelligence import InsightRule
from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from athlete.memory.models import WorkoutMemoryObservation


class _NoOpRule:
    def evaluate(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...],
    ) -> AthleteInsight | None:
        return None


def test_insight_rule_is_a_structural_contract_for_future_registry_entries():
    observation = AthleteObservation(
        id="execution_low:event-1",
        type=AthleteObservationType.EXECUTION_LOW,
        value=70.0,
        confidence=1.0,
        observed_at=datetime(2026, 7, 1, 8),
        evidence=("event-1",),
    )

    rule = _NoOpRule()

    assert isinstance(rule, InsightRule)
    assert rule.evaluate((observation,), ()) is None
