from execution.block_execution import BlockExecution

from execution.block_metrics import BlockMetrics

from timeline.builder import TimelineBuilder

from training.activity import Activity

from workout.models import Workout


class WorkoutExecution:

    def analyze(

        self,

        workout: Workout,

        activity: Activity,

    ):

        timeline = TimelineBuilder().build(

            workout

        )

        result = []

        for block in timeline.blocks:

            metrics = BlockMetrics().calculate(

                block,

                activity,

            )

            target = (

                block.power_from +

                block.power_to

            ) / 2

            if target > 0:

                power_score = max(

                    0,

                    100 -

                    abs(

                        metrics["power"] / target - 1

                    ) * 100,

                )

            else:

                power_score = 100

            cadence_score = 100

            if metrics["cadence"] < block.cadence_from:

                cadence_score -= (

                    block.cadence_from -

                    metrics["cadence"]

                )

            elif metrics["cadence"] > block.cadence_to:

                cadence_score -= (

                    metrics["cadence"] -

                    block.cadence_to

                )

            cadence_score = max(

                0,

                cadence_score,

            )

            hr_score = 100

            execution = (

                power_score * 0.6 +

                cadence_score * 0.2 +

                hr_score * 0.1 +

                metrics["completion"] * 0.1

            )

            result.append(

                BlockExecution(

                    name=block.name,

                    start=block.start,

                    end=block.end,

                    duration=block.duration,

                    completion=metrics["completion"],

                    target_power_from=block.power_from,

                    target_power_to=block.power_to,

                    average_power=metrics["power"],

                    power_score=power_score,

                    target_cadence_from=block.cadence_from,

                    target_cadence_to=block.cadence_to,

                    average_cadence=metrics["cadence"],

                    cadence_score=cadence_score,

                    average_hr=metrics["hr"],

                    hr_score=hr_score,

                    execution_score=execution,

                    comment="OK",

                )

            )

        return result