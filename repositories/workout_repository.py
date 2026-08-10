from dataclasses import dataclass
from datetime import datetime, timedelta

from core.database import Database
from training.analysis.workout_summary import WorkoutSummary


@dataclass(frozen=True)
class PersistedWorkoutRecord:
    file_name: str
    start_time: datetime
    end_time: datetime
    sport: str | None
    duration: int | None
    distance: float | None
    calories: int | None
    normalized_power: float | None
    intensity_factor: float | None
    tss: float | None


class WorkoutRepository:

    def __init__(self, db: Database | None = None):

        self.db = db or Database()

    #
    # SAVE
    #

    def save(
        self,
        file_name: str,
        workout: WorkoutSummary,
    ):

        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO workouts
            (

                file_name,

                start_time,
                end_time,

                sport,

                duration,
                distance,
                calories,

                avg_power,
                normalized_power,
                max_power,

                intensity_factor,
                tss,

                avg_hr,
                max_hr,

                avg_cadence,
                max_cadence,

                z1,
                z2,
                z3,
                z4,
                z5,
                z6,
                z7

            )

            VALUES

            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,
            [

                file_name,

                workout.start,
                workout.end,

                workout.sport,

                workout.duration,
                workout.distance,
                workout.calories,

                workout.average_power,
                workout.normalized_power,
                workout.max_power,

                workout.intensity_factor,
                workout.tss,

                workout.average_hr,
                workout.max_hr,

                workout.average_cadence,
                workout.max_cadence,

                workout.zones.z1,
                workout.zones.z2,
                workout.zones.z3,
                workout.zones.z4,
                workout.zones.z5,
                workout.zones.z6,
                workout.zones.z7,

            ],
        )

    #
    # READ
    #

    def all(self):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            ORDER BY start_time DESC
            """
        ).fetchall()

    def last(self):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            ORDER BY start_time DESC

            LIMIT 1
            """
        ).fetchone()

    def count(self):

        return self.db.connection.execute(
            """
            SELECT COUNT(*)

            FROM workouts
            """
        ).fetchone()[0]

    def exists(
        self,
        file_name: str,
    ) -> bool:

        value = self.db.connection.execute(
            """
            SELECT COUNT(*)

            FROM workouts

            WHERE file_name = ?
            """,
            [file_name],
        ).fetchone()[0]

        return value > 0

    def get_persisted_record(
        self,
        file_name: str,
    ) -> PersistedWorkoutRecord | None:
        row = self.db.connection.execute(
            self._persisted_record_query() + " WHERE file_name = ?",
            [file_name],
        ).fetchone()
        return self._persisted_record(row) if row is not None else None

    def persisted_records_between(
        self,
        start: datetime,
        end: datetime,
    ) -> tuple[PersistedWorkoutRecord, ...]:
        rows = self.db.connection.execute(
            self._persisted_record_query()
            + " WHERE start_time >= ? AND start_time < ? ORDER BY start_time, file_name",
            [start, end],
        ).fetchall()
        return tuple(self._persisted_record(row) for row in rows)

    @staticmethod
    def _persisted_record_query() -> str:
        return """
            SELECT
                file_name, start_time, end_time, sport, duration, distance,
                calories, normalized_power, intensity_factor, tss
            FROM workouts
        """

    @staticmethod
    def _persisted_record(row) -> PersistedWorkoutRecord:
        return PersistedWorkoutRecord(*row)

    #
    # DELETE
    #

    def delete_all(self):

        self.db.connection.execute(
            """
            DELETE FROM workouts
            """
        )

    #
    # QUERIES
    #

    def between(
        self,
        start: datetime,
        end: datetime,
    ):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            WHERE start_time BETWEEN ? AND ?

            ORDER BY start_time
            """,
            [start, end],
        ).fetchall()

    def last_days(
        self,
        days: int,
    ):

        end = datetime.now()

        start = end - timedelta(days=days)

        return self.between(start, end)

    def by_sport(
        self,
        sport: str,
    ):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            WHERE sport = ?

            ORDER BY start_time DESC
            """,
            [sport],
        ).fetchall()

    def by_tss(
        self,
        minimum: float,
        maximum: float,
    ):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            WHERE tss BETWEEN ? AND ?

            ORDER BY start_time DESC
            """,
            [minimum, maximum],
        ).fetchall()

    def latest(
        self,
        limit: int,
    ):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            ORDER BY start_time DESC

            LIMIT ?
            """,
            [limit],
        ).fetchall()

    def since(
        self,
        start: datetime,
    ):

        return self.db.connection.execute(
            """
            SELECT *

            FROM workouts

            WHERE start_time >= ?

            ORDER BY start_time
            """,
            [start],
        ).fetchall()
