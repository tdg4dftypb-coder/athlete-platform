from execution.block_matcher import BlockMatcher

from timeline.models import TimelineBlock

from training.activity import Activity


class BlockMetrics:

    def calculate(

        self,

        block: TimelineBlock,

        activity: Activity,

    ):

        records = BlockMatcher().records(

            block,

            activity,

        )

        if not records:

            return {

                "completion": 0,

                "power": 0,

                "cadence": 0,

                "hr": 0,

            }

        power = [

            r.power

            for r in records

            if r.power is not None

        ]

        cadence = [

            r.cadence

            for r in records

            if r.cadence is not None

        ]

        hr = [

            r.heart_rate

            for r in records

            if r.heart_rate is not None

        ]

        return {

            "completion":

                len(records)

                / block.duration

                * 100,

            "power":

                sum(power) / len(power)

                if power else 0,

            "cadence":

                sum(cadence) / len(cadence)

                if cadence else 0,

            "hr":

                sum(hr) / len(hr)

                if hr else 0,

        }