from core.database import Database
from sleep.sleep_session import SleepSession


class SleepSessionWriter:

    def __init__(self):

        self.db = Database()

    def save(self, session: SleepSession):

        self.db.connection.execute(
            """
            INSERT OR REPLACE INTO sleep_sessions
            (
                sleep_date,
                start_time,
                end_time,
                duration,
                in_bed,
                awake,
                rem,
                core,
                deep,
                efficiency
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.sleep_date,
                session.start,
                session.end,
                session.duration,
                session.in_bed,
                session.awake,
                session.rem,
                session.core,
                session.deep,
                session.efficiency,
            ),
        )