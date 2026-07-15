import duckdb


def main():

    con = duckdb.connect("data/database/health.duckdb")

    result = con.sql("""
        SELECT
            record_type,
            COUNT(*) AS records
        FROM health_records
        GROUP BY record_type
        ORDER BY records DESC
    """)

    result.show(max_rows=100)

    con.close()


if __name__ == "__main__":
    main()