from typing import TYPE_CHECKING

from application.adaptation import AdaptationDirective
from athlete.models import AthleteState

from decision.models import WorkoutPlan
from decision.pipeline.engine import DecisionPipeline
from decision.selection.engine import SelectionEngine

if TYPE_CHECKING:
    from athlete.intelligence.models import AthleteInsight


class DecisionEngine:

    def __init__(self) -> None:

        self.pipeline = DecisionPipeline()
        self.selection = SelectionEngine()

    def decide(
        self,
        athlete: AthleteState,
        adaptation: AdaptationDirective | None = None,
        insights: tuple["AthleteInsight", ...] = (),
    ) -> WorkoutPlan:

        _, prescription = self.pipeline.evaluate(
            athlete,
            adaptation,
            insights,
        )

        return self.selection.select(
            prescription,
        )
