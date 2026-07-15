from core.database import Database


class TrainingSchema:

    def __init__(self):

        self.db = Database()

    def create(self):

        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (

                file_name TEXT PRIMARY KEY,

                start_time TIMESTAMP,
                end_time TIMESTAMP,

                sport TEXT,

                duration INTEGER,
                distance DOUBLE,
                calories INTEGER,

                avg_power DOUBLE,
                normalized_power DOUBLE,
                max_power INTEGER,

                intensity_factor DOUBLE,
                tss DOUBLE,

                avg_hr DOUBLE,
                max_hr INTEGER,

                avg_cadence DOUBLE,
                max_cadence INTEGER,

                z1 INTEGER,
                z2 INTEGER,
                z3 INTEGER,
                z4 INTEGER,
                z5 INTEGER,
                z6 INTEGER,
                z7 INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
            """
        )