from dataclasses import dataclass, field

from decision.models.decision_result import DecisionResult
from decision.models.rule_result import RuleResult
from workout.enums import WorkoutType


@dataclass(slots=True)
class WorkoutPlan:
    scores: dict[WorkoutType, float] = field(default_factory=dict)
    results: list[RuleResult | DecisionResult] = field(default_factory=list)

    def add_result(
        self,
        result: RuleResult | DecisionResult,
    ) -> None:

        self.results.append(result)

        if isinstance(result, DecisionResult):
            self.scores[result.recommendation] = (
                self.scores.get(result.recommendation, 0.0)
                + result.priority
            )
            return

        for workout, score in result.scores.items():
            self.scores[workout] = (
                self.scores.get(workout, 0.0)
                + score
            )

    @property
    def recommendation(self) -> WorkoutType:

        if not self.scores:
            raise ValueError("No workout recommendation available.")

        return max(
            self.scores,
            key=self.scores.get,
        )

    @property
    def decision(self) -> DecisionResult:

        decisions = [

            result

            for result in self.results

            if isinstance(result, DecisionResult)

        ]

        if not decisions:
            raise ValueError(
                "WorkoutPlan does not contain a DecisionResult."
            )

        return max(
            decisions,
            key=lambda decision: decision.priority,
        )