from training.activity import Activity

from timeline.models import TimelineBlock


class BlockMatcher:

    def records(

        self,

        block: TimelineBlock,

        activity: Activity,

    ):

        return [

            record

            for record in activity.records

            if block.start <= record.elapsed_time < block.end

        ]