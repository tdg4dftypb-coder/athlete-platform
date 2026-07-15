from sleep.sleep_builder import SleepBuilder
from sleep.sleep_repository import SleepRepository


def main():

    repository = SleepRepository()

    records = repository.load_records()

    sessions = SleepBuilder().build_sessions(records)

    print(f"\nSleep sessions: {len(sessions)}\n")

    for date, summary in list(sessions.items())[-10:]:

        print(date)

        print(summary)

        print()


if __name__ == "__main__":
    main()