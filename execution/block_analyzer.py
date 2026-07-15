from execution.block_models import BlockExecution

from execution.timeline_matcher import TimelineMatcher

from timeline.models import TimelineBlock

from training.activity import Activity


class BlockAnalyzer:

    def analyze(

        self,

        block: TimelineBlock,

        activity: Activity,

    ) -> BlockExecution:

        records = TimelineMatcher().match(

            block,

            activity,

        )

        if not records:

            return BlockExecution(

                name=block.name,

                planned_start=block.start,

                planned_end=block.end,

                actual_start=0,

                actual_end=0,

                planned_power_from=block.power_from,

                planned_power_to=block.power_to,

                actual_power=0,

                planned_cadence_from=block.cadence_from,

                planned_cadence_to=block.cadence_to,

                actual_cadence=0,

                completion=0,

                power_score=0,

                cadence_score=0,

                execution_score=0,

                comment="Block not completed.",

            )

        avg_power = sum(

            r.power

            for r in records

            if r.power is not None

        ) / len(records)

        cadence = [

            r.cadence

            for r in records

            if r.cadence is not None

        ]

        avg_cadence = (

            sum(cadence) / len(cadence)

            if cadence

            else 0

        )

        target = (

            block.power_from +

            block.power_to

        ) / 2

        ratio = avg_power / target

        power_score = max(

            0,

            100 - abs(1 - ratio) * 100,

        )

        completion = (

            len(records) /

            block.duration

        ) * 100

        cadence_score = 100

        if avg_cadence < block.cadence_from:

            cadence_score -= (

                block.cadence_from -

                avg_cadence

            )

        elif avg_cadence > block.cadence_to:

            cadence_score -= (

                avg_cadence -

                block.cadence_to

            )

        cadence_score = max(

            0,

            cadence_score,

        )

        execution = (

            power_score * 0.7 +

            cadence_score * 0.3

        )

        return BlockExecution(

            name=block.name,

            planned_start=block.start,

            planned_end=block.end,

            actual_start=records[0].elapsed_time,

            actual_end=records[-1].elapsed_time,

            planned_power_from=block.power_from,

            planned_power_to=block.power_to,

            actual_power=avg_power,

            planned_cadence_from=block.cadence_from,

            planned_cadence_to=block.cadence_to,

            actual_cadence=avg_cadence,

            completion=completion,

            power_score=power_score,

            cadence_score=cadence_score,

            execution_score=execution,

            comment="OK",

        )