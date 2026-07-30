from execution.result import BlockExecutionResult

from execution.timeline_matcher import TimelineMatcher

from timeline.models import TimelineBlock

from training.activity import Activity


class BlockAnalyzer:

    def analyze(

        self,

        block: TimelineBlock,

        activity: Activity,

    ) -> BlockExecutionResult:

        records = TimelineMatcher().match(

            block,

            activity,

        )


        if not records:

            return BlockExecutionResult(

                name=block.name,

                planned_duration=block.duration,

                executed_duration=0,

                completion_score=0,

                power_score=None,

                cadence_score=None,

                heart_rate_score=None,

                execution_score=0,

                deviations=[

                    "Block not completed.",

                ],

            )


        power_values = [

            r.power

            for r in records

            if r.power is not None

        ]


        avg_power = (

            sum(power_values)

            / len(power_values)

            if power_values

            else None

        )


        cadence_values = [

            r.cadence

            for r in records

            if r.cadence is not None

        ]


        avg_cadence = (

            sum(cadence_values)

            / len(cadence_values)

            if cadence_values

            else None

        )


        power_score = None


        if avg_power is not None:

            target = (

                block.power_from

                +

                block.power_to

            ) / 2


            if target > 0:

                power_score = max(

                    0,

                    100

                    -

                    abs(

                        1

                        -

                        avg_power / target

                    )

                    * 100,

                )


        cadence_score = None


        if avg_cadence is not None:

            cadence_score = 100


            if avg_cadence < block.cadence_from:

                cadence_score -= (

                    block.cadence_from

                    -

                    avg_cadence

                )


            elif avg_cadence > block.cadence_to:

                cadence_score -= (

                    avg_cadence

                    -

                    block.cadence_to

                )


            cadence_score = max(

                0,

                cadence_score,

            )


        available_scores = [

            score

            for score in (

                power_score,

                cadence_score,

            )

            if score is not None

        ]


        execution_score = (

            sum(available_scores)

            /

            len(available_scores)

            if available_scores

            else 0

        )


        return BlockExecutionResult(

            name=block.name,

            planned_duration=block.duration,

            executed_duration=round(

                records[-1].elapsed_time

                -

                records[0].elapsed_time

            ),

            completion_score=min(

                100,

                round(

                    len(records)

                    /

                    block.duration

                    *

                    100,

                    1,

                ),

            ),

            power_score=power_score,

            cadence_score=cadence_score,

            heart_rate_score=None,

            execution_score=round(

                execution_score,

                1,

            ),

            deviations=[],

        )