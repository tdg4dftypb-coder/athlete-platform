from schema.health_schema import HealthSchema
from schema.sleep_schema import SleepSchema
from schema.training_schema import TrainingSchema


def main():

    print()

    print("Initializing database...")

    HealthSchema().create()

    SleepSchema().create()

    TrainingSchema().create()

    print("Done.")

    print()


if __name__ == "__main__":
    main()