from athlete.state_builder import AthleteStateBuilder

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository


def main():

    repository = HealthRepository()

    history = repository.load_daily()

    health = ContextBuilder().build(history)

    recovery = RecoveryEngine().analyze(health)

    performance = PerformanceEngine().analyze()

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=None,

    )

    print()

    print(athlete)

    print()


if __name__ == "__main__":
    main()