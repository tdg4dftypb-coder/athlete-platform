from planner.dsl.models import (
    Interval,
    Repeat,
    Workout,
)

from planner.models import PlannedBlock


class DSLCompiler:

    def compile(
        self,
        workout: Workout,
    ) -> list[PlannedBlock]:

        blocks = []

        self._compile_nodes(
            workout.children,
            blocks,
        )

        return blocks


    def _compile_nodes(
        self,
        nodes,
        blocks,
    ):

        for node in nodes:

            if isinstance(
                node,
                Interval,
            ):

                blocks.append(
                    PlannedBlock(
                        name=node.name,
                        description=node.name,
                        duration=node.duration,
                        power_from=node.power_from,
                        power_to=node.power_to,
                        cadence_from=node.cadence_from,
                        cadence_to=node.cadence_to,
                    )
                )


            elif isinstance(
                node,
                Repeat,
            ):

                for _ in range(node.count):

                    self._compile_nodes(
                        node.children,
                        blocks,
                    )