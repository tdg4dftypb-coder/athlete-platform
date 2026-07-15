from core.database import Database


db = Database()

print()

rows = db.connection.execute(
    """
    SELECT *

    FROM workouts

    LIMIT 1
    """
).fetchall()

print("Rows:")
print(rows)

print()

cursor = db.connection.execute(
    """
    SELECT *

    FROM workouts

    LIMIT 1
    """
)

print("Columns:")

for i, column in enumerate(cursor.description):
    print(i, column)

print()