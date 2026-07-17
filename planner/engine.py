from decision.models import DecisionState

from planner.dsl.compiler import DSLCompiler
from planner.dsl.parser import DSLParser

from planner.models import PlannedWorkout


class PlannerEngine:

    def __init__(self):

        self.parser = DSLParser()

        self.compiler = DSLCompiler()

    def build(
        self,
        decision: DecisionState,
    ) -> PlannedWorkout:

        #
        # DSL
        #

        if decision.recommendation == "REST":

            return PlannedWorkout(

                name="Rest Day",

                sport=decision.sport.value,

                target_tss=0,

                estimated_duration=0,

                blocks=[],

            )

        if decision.recommendation == "RECOVERY":

            dsl = self.parser.recovery()

        elif decision.recommendation == "ENDURANCE":

            dsl = self.parser.endurance()

        elif decision.recommendation == "TEMPO":

            dsl = self.parser.tempo()

        elif decision.recommendation == "THRESHOLD":

            dsl = self.parser.threshold()

        else:

            dsl = self.parser.vo2()

        #
        # Blocks
        #

        blocks = self.compiler.compile(dsl)

        duration = sum(

            block.duration

            for block in blocks

        ) // 60

        #
        # Plan
        #

        return PlannedWorkout(

            name=dsl.name,

            sport=decision.sport.value,

            target_tss=decision.target_tss,

            estimated_duration=duration,

            blocks=blocks,

        )