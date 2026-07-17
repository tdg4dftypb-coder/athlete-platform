from dataclasses import dataclass, field

from decision.models.rule_result import RuleResult
from workout.enums import WorkoutType


@dataclass(slots=True)
class WorkoutPlan:
    scores: dict[WorkoutType, float] = field(default_factory=dict)
    results: list[RuleResult] = field(default_factory=list)

    def add_result(self, result: RuleResult) -> None:

        self.results.append(result)

        for workout, score in result.scores.items():
            self.scores[workout] = (
                self.scores.get(workout, 0.0) + score
            )

    @property
    def recommendation(self) -> WorkoutType:

        if not self.scores:
            raise ValueError("No workout recommendation available.")

        return max(
            self.scores,
            key=self.scores.get,
        )