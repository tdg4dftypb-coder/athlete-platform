from pathlib import Path

from training.parsers.fit_parser import FitParser


def main():

    activities = Path("/Users/marsm0wa/Documents/Zwift/Activities")
    fit_file = sorted(activities.glob("*.fit"))[-1]

    activity = FitParser().parse(str(fit_file))

    powers = [
        r.power
        for r in activity.records
        if r.power is not None
    ]

    print(f"Samples: {len(powers)}")
    print(f"Average: {sum(powers)/len(powers):.2f}")

    zones = [
        (0, 100),
        (100, 200),
        (200, 300),
        (300, 500),
        (500, 800),
        (800, 1000),
        (1000, 2000),
    ]

    print()

    for low, high in zones:

        count = sum(
            1
            for p in powers
            if low <= p < high
        )

        print(
            f"{low:4}-{high:<4}: "
            f"{count:5} "
            f"({count/len(powers)*100:5.1f}%)"
        )


if __name__ == "__main__":
    main()