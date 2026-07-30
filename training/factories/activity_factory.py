from training.activity import Activity, ActivityRecord
from training.ingestion.parsed_activity import ParsedActivity


class ActivityFactory:
    """Builds a domain Activity from parsed ingestion data."""

    def create(
        self,
        parsed: ParsedActivity,
    ) -> Activity:

        records = sorted(
            (
                record
                for record in parsed.records
                if record.timestamp is not None
            ),
            key=lambda record: record.timestamp,
        )

        if records:

            start = parsed.start or records[0].timestamp
            end = parsed.end or records[-1].timestamp
            first = records[0].timestamp

            activity_records = [
                ActivityRecord(
                    timestamp=record.timestamp,
                    elapsed_time=int(
                        (record.timestamp - first)
                        .total_seconds()
                    ),
                    power=(
                        float(record.power)
                        if record.power is not None
                        else None
                    ),
                    heart_rate=record.heart_rate,
                    cadence=(
                        float(record.cadence)
                        if record.cadence is not None
                        else None
                    ),
                    speed=record.speed,
                )
                for record in records
            ]

            duration = activity_records[-1].elapsed_time

        else:

            if parsed.start is None:
                raise ValueError(
                    "Parsed activity without records requires a start time."
                )

            start = parsed.start
            end = parsed.end or start
            activity_records = []
            duration = 0

        return Activity(
            start=start,
            end=end,
            sport=parsed.sport or "unknown",
            distance=parsed.distance,
            calories=parsed.calories,
            duration=duration,
            records=activity_records,
        )
