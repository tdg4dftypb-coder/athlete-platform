from pathlib import Path

import duckdb


class Database:

    def __init__(self, db_path="data/database/health.duckdb"):

        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = duckdb.connect(
            str(self.db_path)
        )

    def close(self):

        self.connection.close()