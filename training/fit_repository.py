from training.training_database import TrainingDatabase
from training.analysis.workout_summary import WorkoutSummary
from training.activity import Activity


class FitRepository:

    def __init__(self):

        self.db = TrainingDatabase()

        self.db.create()

    def save(
        self,
        activity: Activity,
        workout: WorkoutSummary,
    ):

        self.db.db.connection.execute(
            """
            INSERT INTO workouts
            (
                start_time,
                end_time,
                sport,
                duration,
                avg_power,
                normalized_power,
                avg_hr,
                max_hr,
                avg_cadence,
                distance
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                activity.start,
                activity.end,
                activity.sport,
                workout.duration,
                workout.average_power,
                workout.normalized_power,
                workout.average_hr,
                workout.max_hr,
                workout.average_cadence,
                float(activity.distance),
            ],
        )

    def all(self):

        return self.db.db.connection.execute(
            """
            SELECT
                start_time,
                end_time,
                sport,
                duration,
                avg_power,
                normalized_power,
                avg_hr,
                max_hr,
                avg_cadence,
                distance
            FROM workouts
            ORDER BY start_time DESC
            """
        ).fetchall()
