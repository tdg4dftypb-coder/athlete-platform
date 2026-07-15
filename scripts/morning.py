from repositories.health_repository import HealthRepository
from engines.context_builder import ContextBuilder
from recovery.engine import RecoveryEngine


def main():

    repository = HealthRepository()

    days = repository.load_daily()

    context = ContextBuilder().build(days)

    recovery = RecoveryEngine().analyze(context)

    print()
    print("=" * 50)
    print("ATHLETE PLATFORM")
    print("=" * 50)
    print()

    print(f"Recovery : {recovery.score}/100")
    print(f"Status   : {recovery.status}")

    print()

    print("Reasons:")

    if recovery.reasons:

        for reason in recovery.reasons:
            print(f" • {reason}")

    else:

        print(" • Brak istotnych zmian.")

    print()

    print("Today's metrics")

    print(f"HRV      : {context.today.hrv}")
    print(f"RHR      : {context.today.resting_hr}")
    print(f"Sleep    : {context.today.sleep_duration} min")
    print(f"Steps    : {context.today.steps}")

    print()


if __name__ == "__main__":
    main()