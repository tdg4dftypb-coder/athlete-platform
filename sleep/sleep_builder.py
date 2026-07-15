from collections import defaultdict
from datetime import datetime, timedelta

from sleep.sleep_models import SleepSummary
from sleep.sleep_session import SleepSession

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S %z"


class SleepBuilder:

    def build_sessions(self, records):

        grouped = defaultdict(list)

        for record in records:

            start = datetime.strptime(
                record["start_date"],
                DATETIME_FORMAT,
            )

            sleep_date = start.date()

            if start.hour < 12:
                sleep_date -= timedelta(days=1)

            grouped[sleep_date].append(record)

        sessions = []

        for sleep_date, session_records in grouped.items():

            summary = self.build(session_records)

            start = min(
                datetime.strptime(
                    r["start_date"],
                    DATETIME_FORMAT,
                )
                for r in session_records
            )

            end = max(
                datetime.strptime(
                    r["end_date"],
                    DATETIME_FORMAT,
                )
                for r in session_records
            )

            sessions.append(
                SleepSession(
                    sleep_date=sleep_date,
                    start=start,
                    end=end,
                    duration=summary.duration,
                    in_bed=summary.in_bed,
                    awake=summary.awake,
                    rem=summary.rem,
                    core=summary.core,
                    deep=summary.deep,
                    efficiency=summary.efficiency,
                )
            )

        return sessions

    def build(self, records):

        summary = SleepSummary()

        for record in records:

            start = datetime.strptime(
                record["start_date"],
                DATETIME_FORMAT,
            )

            end = datetime.strptime(
                record["end_date"],
                DATETIME_FORMAT,
            )

            minutes = int(
                (end - start).total_seconds() / 60
            )

            value = record["text_value"]

            if value == "HKCategoryValueSleepAnalysisAsleepCore":
                summary.core += minutes
                summary.duration += minutes

            elif value == "HKCategoryValueSleepAnalysisAsleepREM":
                summary.rem += minutes
                summary.duration += minutes

            elif value == "HKCategoryValueSleepAnalysisAsleepDeep":
                summary.deep += minutes
                summary.duration += minutes

            elif value == "HKCategoryValueSleepAnalysisAsleepUnspecified":
                summary.duration += minutes

            elif value == "HKCategoryValueSleepAnalysisAwake":
                summary.awake += minutes

            elif value == "HKCategoryValueSleepAnalysisInBed":
                summary.in_bed += minutes

        if summary.in_bed == 0:
            summary.in_bed = summary.duration + summary.awake

        return summary