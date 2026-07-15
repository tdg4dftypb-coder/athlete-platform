from pathlib import Path

from repositories.workout_repository import WorkoutRepository
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer


WORKOUTS = Path(
    "/Users/marsm0wa/Documents/Zwift/Activities"
)


def main():

    parser = FitParser()

    analyzer = WorkoutAnalyzer()

    repository = WorkoutRepository()

    files = sorted(
        WORKOUTS.glob("*.fit")
    )

    print()

    print(f"Importing {len(files)} workouts...")

    print()

    imported = 0

    for file in files:

        if repository.exists(file.name):

            print(f"• {file.name} (exists)")

            continue

        activity = parser.parse(str(file))

        workout = analyzer.analyze(activity)

        repository.save(

            file_name=file.name,

            workout=workout,

        )

        imported += 1

        print(f"✓ {file.name}")

    print()

    print("------------------------------")

    print("Imported :", imported)

    print("Files    :", len(files))

    print("Done.")

    print()


if __name__ == "__main__":
    main()