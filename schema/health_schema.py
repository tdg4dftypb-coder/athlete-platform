from core.database import Database


class HealthSchema:

    def __init__(self, db=None):

        self.db = db or Database()

    def create(self):

        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS health_records (

                id BIGINT,

                record_type VARCHAR,

                source_name VARCHAR,

                unit VARCHAR,

                start_date VARCHAR,

                end_date VARCHAR,

                numeric_value DOUBLE,

                text_value VARCHAR,

                provider VARCHAR,
                external_id VARCHAR,
                deleted BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP

            )
            """
        )

        for definition in (
            "provider VARCHAR",
            "external_id VARCHAR",
            "deleted BOOLEAN DEFAULT FALSE",
            "updated_at TIMESTAMP",
        ):
            self.db.connection.execute(
                f"ALTER TABLE health_records ADD COLUMN IF NOT EXISTS {definition}"
            )

        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_health (

                date DATE PRIMARY KEY,

                weight DOUBLE,

                sleep_duration INTEGER,

                sleep_score INTEGER,

                hrv DOUBLE,

                resting_hr DOUBLE,

                active_energy DOUBLE,

                resting_energy DOUBLE,

                steps BIGINT,

                respiratory_rate DOUBLE,

                spo2 DOUBLE,

                wrist_temperature DOUBLE

            )
            """
        )
