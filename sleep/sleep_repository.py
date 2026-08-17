from core.database import Database


class SleepRepository:

    def __init__(self, database=None):

        self.db = database if database is not None else Database()

    def load_records(self):

        table_exists = self.db.connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='health_records'"
        ).fetchone()[0]
        if not table_exists:
            return []

        has_deleted = self.db.connection.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='health_records' AND column_name='deleted'"
        ).fetchone()[0]
        active_filter = "AND COALESCE(deleted, FALSE) = FALSE" if has_deleted else ""

        rows = self.db.connection.execute(
            f"""
            SELECT

                start_date,
                end_date,
                text_value

            FROM health_records

            WHERE record_type='HKCategoryTypeIdentifierSleepAnalysis'
            {active_filter}

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
