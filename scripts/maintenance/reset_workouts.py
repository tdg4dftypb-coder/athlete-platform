from core.database import Database


db = Database()

db.connection.execute(
    """
    DROP TABLE IF EXISTS workouts
    """
)

print("workouts table dropped.")