from builders.daily_health_writer import DailyHealthWriter
from repositories.health_repository import HealthRepository


def main():

    repository = HealthRepository()

    writer = DailyHealthWriter()

    days = repository.load_daily()

    print(f"Saving {len(days)} days...\n")

    for index, day in enumerate(days, start=1):

        writer.save(day)

        if index % 100 == 0:
            print(f"{index} / {len(days)}")

    print("\nDone.")


if __name__ == "__main__":
    main()