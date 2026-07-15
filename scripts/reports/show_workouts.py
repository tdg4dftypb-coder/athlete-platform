from training.fit_repository import FitRepository


def main():

    repository = FitRepository()

    workouts = repository.all()

    print()

    print(f"Workouts: {len(workouts)}")

    print()

    for workout in workouts:

        print(workout)

        print()


if __name__ == "__main__":
    main()