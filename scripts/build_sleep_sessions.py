from sleep.sleep_builder import SleepBuilder
from sleep.sleep_repository import SleepRepository
from sleep.sleep_session_writer import SleepSessionWriter


def main():

    repository = SleepRepository()

    builder = SleepBuilder()

    writer = SleepSessionWriter()

    records = repository.load_records()

    sessions = builder.build_sessions(records)

    print(f"\nSaving {len(sessions)} sleep sessions...\n")

    for index, session in enumerate(sessions, start=1):

        writer.save(session)

        if index % 100 == 0:
            print(f"{index} / {len(sessions)}")

    print("\nDone.")


if __name__ == "__main__":
    main()