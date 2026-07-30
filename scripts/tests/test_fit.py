from pathlib import Path

from training.factories.activity_factory import ActivityFactory
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer


ACTIVITIES = Path(
    "/Users/marsm0wa/Documents/Zwift/Activities"
)


def main():

    file = sorted(ACTIVITIES.glob("*.fit"))[-1]

    parsed_activity = FitParser().parse(str(file))

    activity = ActivityFactory().create(parsed_activity)

    workout = WorkoutAnalyzer().analyze(activity)

    print()

    print("Duration :", workout.duration)

    print("Avg Power:", round(workout.average_power))

    print("NP       :", round(workout.normalized_power))

    print("IF       :", round(workout.intensity_factor, 2))

    print("TSS      :", workout.tss)

    print("Max Power:", workout.max_power)

    print("Avg HR   :", round(workout.average_hr))

    print("Max HR   :", workout.max_hr)

    print("Avg Cad  :", round(workout.average_cadence))

    print("Max Cad  :", workout.max_cadence)

    print()


if __name__ == "__main__":
    main()
