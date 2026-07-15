from timeline.models import TimelineBlock

from training.activity import Activity


class TimelineMatcher:

    def match(

        self,

        block: TimelineBlock,

        activity: Activity,

    ):

        records = []

        for record in activity.records:

            if (

                record.elapsed_time >= block.start

                and

                record.elapsed_time < block.end

            ):

                records.append(record)

        return records