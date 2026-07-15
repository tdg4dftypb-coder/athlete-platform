from core.database import Database


class SleepRepository:

    def __init__(self):

        self.db = Database()

    def load_records(self):

        rows = self.db.connection.execute(
            """
            SELECT

                start_date,
                end_date,
                text_value

            FROM health_records

            WHERE record_type='HKCategoryTypeIdentifierSleepAnalysis'

            ORDER BY start_date
            """
        ).fetchall()

        records = []

        for start, end, value in rows:

            records.append(
                {
                    "start_date": start,
                    "end_date": end,
                    "text_value": value,
                }
            )

        return records