from collections import defaultdict
from datetime import datetime

from core.database import Database
from core.models import HealthDaily

from sleep.sleep_builder import SleepBuilder
from sleep.sleep_repository import SleepRepository


class HealthRepository:

    def __init__(self, database=None):

        self.db = database if database is not None else Database()

        sessions = SleepBuilder().build_sessions(
            SleepRepository(database=self.db).load_records()
        )

        self.sleep_sessions = {
            session.sleep_date: session
            for session in sessions
        }

    def load_daily(self):

        has_deleted = self.db.connection.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='health_records' AND column_name='deleted'"
        ).fetchone()[0]
        active_filter = "AND COALESCE(deleted, FALSE) = FALSE" if has_deleted else ""

        rows = self.db.connection.execute(
            f"""
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
            {active_filter}

            ORDER BY date
            """
        ).fetchall()

        grouped = defaultdict(list)

        for day, record_type, value in rows:

            grouped[day].append((record_type, value))

        history = []

        for day, records in grouped.items():

            values = {}

            #
            # Sum cumulative metrics.
            #

            values["HKQuantityTypeIdentifierStepCount"] = 0
            values["HKQuantityTypeIdentifierActiveEnergyBurned"] = 0
            values["HKQuantityTypeIdentifierBasalEnergyBurned"] = 0

            for record_type, value in records:

                if record_type in (
                    "HKQuantityTypeIdentifierStepCount",
                    "HKQuantityTypeIdentifierActiveEnergyBurned",
                    "HKQuantityTypeIdentifierBasalEnergyBurned",
                ):

                    values[record_type] += value

                else:

                    values[record_type] = value

            sleep = self.sleep_sessions.get(
                datetime.strptime(
                    day,
                    "%Y-%m-%d"
                ).date()
            )

            history.append(

                HealthDaily(

                    date=datetime.strptime(
                        day,
                        "%Y-%m-%d"
                    ).date(),

                    weight=values.get(
                        "HKQuantityTypeIdentifierBodyMass"
                    ),

                    sleep_duration=(
                        sleep.duration
                        if sleep
                        else None
                    ),

                    sleep_score=(
                        round(sleep.efficiency)
                        if sleep and sleep.efficiency is not None
                        else None
                    ),

                    hrv=values.get(
                        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
                    ),

                    resting_hr=values.get(
                        "HKQuantityTypeIdentifierRestingHeartRate"
                    ),

                    active_energy=values.get(
                        "HKQuantityTypeIdentifierActiveEnergyBurned"
                    ),

                    resting_energy=values.get(
                        "HKQuantityTypeIdentifierBasalEnergyBurned"
                    ),

                    steps=values.get(
                        "HKQuantityTypeIdentifierStepCount"
                    ),

                    respiratory_rate=values.get(
                        "HKQuantityTypeIdentifierRespiratoryRate"
                    ),

                    spo2=values.get(
                        "HKQuantityTypeIdentifierOxygenSaturation"
                    ),

                    wrist_temperature=values.get(
                        "HKQuantityTypeIdentifierAppleSleepingWristTemperature"
                    ),

                )

            )

        return history
