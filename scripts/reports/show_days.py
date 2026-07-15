from repositories.health_repository import HealthRepository


def main():

    repository = HealthRepository()

    days = repository.load_daily()

    print(f"\nHealthDaily objects: {len(days)}\n")

    for day in days[-15:]:
        print(day)


if __name__ == "__main__":
    main()