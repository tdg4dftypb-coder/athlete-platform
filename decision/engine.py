from athlete.models import AthleteState

from decision.models import WorkoutPlan
from decision.pipeline.engine import DecisionPipeline
from decision.selection.engine import SelectionEngine


class DecisionEngine:

    def __init__(self) -> None:

        self.pipeline = DecisionPipeline()
        self.selection = SelectionEngine()

    def decide(
        self,
        athlete: AthleteState,
    ) -> WorkoutPlan:

        _, prescription = self.pipeline.evaluate(
            athlete,
        )

        return self.selection.select(
            prescription,
        )