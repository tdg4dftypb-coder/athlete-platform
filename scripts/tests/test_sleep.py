from duckdb import connect

from sleep.sleep_builder import SleepBuilder


def main():

    con = connect("data/database/health.duckdb")

    date = con.sql("""
        SELECT
            split_part(start_date, ' ', 1)
        FROM health_records
        WHERE record_type = 'HKCategoryTypeIdentifierSleepAnalysis'
        ORDER BY start_date DESC
        LIMIT 1
    """).fetchone()[0]

    rows = con.sql(f"""
        SELECT
            start_date,
            end_date,
            text_value
        FROM health_records
        WHERE
            record_type = 'HKCategoryTypeIdentifierSleepAnalysis'
            AND split_part(start_date, ' ', 1) = '{date}'
        ORDER BY start_date
    """).fetchall()

    records = []

    for start_date, end_date, text_value in rows:

        records.append(
            {
                "start_date": start_date,
                "end_date": end_date,
                "text_value": text_value,
            }
        )

    summary = SleepBuilder().build(records)

    print(f"\nSleep date: {date}\n")

    print(summary)


if __name__ == "__main__":
    main()