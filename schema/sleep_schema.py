from core.database import Database


class SleepSchema:

    def __init__(self):

        self.db = Database()

    def create(self):

        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sleep_sessions (

                sleep_date DATE PRIMARY KEY,

                start_time TIMESTAMP,

                end_time TIMESTAMP,

                duration INTEGER,

                in_bed INTEGER,

                awake INTEGER,

                rem INTEGER,

                core INTEGER,

                deep INTEGER,

                efficiency DOUBLE

            )
            """
        )