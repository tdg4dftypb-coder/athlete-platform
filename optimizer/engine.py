from simulator.engine import SimulatorEngine

from workout.models import Workout


class OptimizerEngine:

    TOLERANCE = 2.0

    MAX_ITERATIONS = 20

    def __init__(self):

        self.simulator = SimulatorEngine()

    def optimize(
        self,
        workout: Workout,
    ) -> Workout:

        for _ in range(self.MAX_ITERATIONS):

            simulation = self.simulator.simulate(workout)

            error = (

                simulation.tss
                - workout.target_tss

            )

            if abs(error) <= self.TOLERANCE:

                return workout

            factor = (

                workout.target_tss
                / simulation.tss

            )

            for block in workout.blocks:

                block.duration = max(

                    60,

                    int(block.duration * factor)

                )

        return workout