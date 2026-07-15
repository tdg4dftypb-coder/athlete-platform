from collections import defaultdict
from datetime import datetime

from builders.health_daily_builder import HealthDailyBuilder
from core.database import Database
from sleep.sleep_builder import SleepBuilder
from sleep.sleep_repository import SleepRepository


class HealthRepository:

    def __init__(self):

        self.db = Database()
        self.builder = HealthDailyBuilder()

        sessions = SleepBuilder().build_sessions(
            SleepRepository().load_records()
        )

        self.sleep_sessions = {
            session.sleep_date: session
            for session in sessions
        }

    def load_daily(self):

        rows = self.db.connection.execute(
            """
            SELECT

                split_part(start_date, ' ', 1) AS date,

                record_type,

                numeric_value

            FROM health_records

            WHERE record_type IN (

                'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',

                'HKQuantityTypeIdentifierRestingHeartRate',

                'HKQuantityTypeIdentifierBodyMass',

                'HKQuantityTypeIdentifierStepCount',

                'HKQuantityTypeIdentifierActiveEnergyBurned',

                'HKQuantityTypeIdentifierBasalEnergyBurned',

                'HKQuantityTypeIdentifierRespiratoryRate',

                'HKQuantityTypeIdentifierOxygenSaturation',

                'HKQuantityTypeIdentifierAppleSleepingWristTemperature'

            )

            ORDER BY date
            """
        ).fetchall()

        grouped = defaultdict(list)

        for date, record_type, value in rows:

            grouped[date].append(
                {
                    "date": date,
                    "record_type": record_type,
                    "value": value,
                }
            )

        days = []

        for date_str, records in grouped.items():

            sleep = self.sleep_sessions.get(
                datetime.strptime(
                    date_str,
                    "%Y-%m-%d"
                ).date()
            )

            days.append(
                self.builder.build(
                    records,
                    sleep=sleep,
                )
            )

        return days