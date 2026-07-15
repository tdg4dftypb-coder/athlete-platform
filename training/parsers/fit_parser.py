from fitparse import FitFile

from training.raw_activity import RawActivity, RawRecord


class FitParser:

    def parse(self, path: str) -> RawActivity:

        fit = FitFile(path)

        session = next(fit.get_messages("session"))

        values = {
            field.name: field.value
            for field in session
        }

        records = []

        for message in fit.get_messages("record"):

            fields = {
                field.name: field.value
                for field in message
            }

            records.append(
                RawRecord(
                    timestamp=fields.get("timestamp"),
                    power=fields.get("power"),
                    heart_rate=fields.get("heart_rate"),
                    cadence=fields.get("cadence"),
                    speed=fields.get("enhanced_speed"),
                )
            )

        return RawActivity(
            start=values.get("start_time"),
            end=values.get("timestamp"),
            sport=values.get("sport"),
            distance=values.get("total_distance", 0.0),
            calories=values.get("total_calories", 0),
            records=records,
        )