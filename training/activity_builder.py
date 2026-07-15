from training.activity import Activity
from training.activity import ActivityRecord

from training.raw_activity import RawActivity


class ActivityBuilder:

    def build(
        self,
        raw: RawActivity,
    ) -> Activity:

        records = []

        if not raw.records:

            return Activity(

                start=raw.start,

                end=raw.end,

                sport=raw.sport,

                distance=raw.distance,

                calories=raw.calories,

                duration=0,

                records=[],

            )

        first = raw.records[0].timestamp

        for record in raw.records:

            elapsed = int(

                (record.timestamp - first)

                .total_seconds()

            )

            records.append(

                ActivityRecord(

                    timestamp=record.timestamp,

                    elapsed_time=elapsed,

                    power=record.power,

                    heart_rate=record.heart_rate,

                    cadence=record.cadence,

                    speed=record.speed,

                )

            )

        duration = records[-1].elapsed_time

        return Activity(

            start=raw.start,

            end=raw.end,

            sport=raw.sport,

            distance=raw.distance,

            calories=raw.calories,

            duration=duration,

            records=records,

        )