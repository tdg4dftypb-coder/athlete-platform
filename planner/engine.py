from athlete.models import AthleteState

from decision.models import DecisionResult

from planner.dsl.compiler import DSLCompiler
from planner.dsl.parser import DSLParser
from planner.models import PlannedWorkout
from planner.selection import SelectionEngine
from planner.selection.models import SelectionContext


class PlannerEngine:

    def __init__(self):

        self.selection = SelectionEngine()

        self.parser = DSLParser()

        self.compiler = DSLCompiler()


    def build(
        self,
        decision: DecisionResult,
        athlete: AthleteState,
    ) -> PlannedWorkout:

        context = SelectionContext(
            available_minutes=athlete.context.available_minutes
            if hasattr(
                athlete.context,
                "available_minutes",
            )
            else 60,

            target_tss=decision.target_tss,

            workout_type=decision.recommendation,

            recovery_score=athlete.recovery.score,

            fatigue_score=athlete.performance.fatigue,
        )

        recipe = self.selection.select(
            decision.recommendation,
            context,
        )

        dsl = self.parser.build(
            recipe,
        )

        blocks = self.compiler.compile(
            dsl,
        )

        duration = sum(
            block.duration
            for block in blocks
        ) // 60

        return PlannedWorkout(
            name=dsl.name,
            sport=decision.sport.value,
            target_tss=recipe.prescription.target_tss,
            estimated_duration=duration,
            blocks=blocks,
        )