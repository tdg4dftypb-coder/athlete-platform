import duckdb


def main():

    con = duckdb.connect("data/database/health.duckdb")

    result = con.sql("""
        SELECT
            text_value,
            COUNT(*) AS records
        FROM health_records
        WHERE record_type = 'HKCategoryTypeIdentifierSleepAnalysis'
        GROUP BY text_value
        ORDER BY records DESC
    """)

    result.show(max_rows=20)

    con.close()


if __name__ == "__main__":
    main()