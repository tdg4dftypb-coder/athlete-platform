from core.database import Database
from collectors.apple_health.parser import AppleHealthParser
from schema.health_schema import HealthSchema


class AppleHealthImporter:

    def __init__(self, xml_path):

        self.db = Database()
        self.parser = AppleHealthParser(xml_path)

    def run(self):

        HealthSchema(self.db).create()

        connection = self.db.connection

        count = 0

        batch = []

        for record in self.parser.records():

            numeric_value = None
            text_value = None

            value = record["value"]

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                text_value = value

            batch.append(
                (
                    record["type"],
                    record["source_name"],
                    record["unit"],
                    record["start_date"],
                    record["end_date"],
                    numeric_value,
                    text_value,
                )
            )

            count += 1

            if len(batch) >= 5000:

                connection.executemany(
                    """
                    INSERT INTO health_records
                    (
                        record_type,
                        source_name,
                        unit,
                        start_date,
                        end_date,
                        numeric_value,
                        text_value
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )

                batch.clear()

                print(f"{count:,} records imported...")

        if batch:

            connection.executemany(
                """
                INSERT INTO health_records
                (
                    record_type,
                    source_name,
                    unit,
                    start_date,
                    end_date,
                    numeric_value,
                    text_value
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )

        print(f"\nFinished: {count:,} records.")

        self.db.close()
