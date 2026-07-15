from pathlib import Path

from training.activity_builder import ActivityBuilder
from training.parsers.fit_parser import FitParser


def main():

    activities = Path(
        "/Users/marsm0wa/Documents/Zwift/Activities"
    )

    fit = sorted(
        activities.glob("*.fit")
    )[-1]

    raw = FitParser().parse(
        str(fit)
    )

    activity = ActivityBuilder().build(
        raw
    )

    print()

    print("=" * 60)

    print("ACTIVITY")

    print("=" * 60)

    print()

    print("Duration :", activity.duration)

    print("Records  :", len(activity.records))

    print()

    print("First five records")

    print()

    for record in activity.records[:5]:

        print(

            record.elapsed_time,

            record.power,

            record.cadence,

            record.heart_rate,

        )

    print()


if __name__ == "__main__":
    main()