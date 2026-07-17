from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from athlete.state_builder import AthleteStateBuilder
from decision.engine import DecisionEngine
from engines.context_builder import ContextBuilder
from health.engine import HealthEngine
from performance.engine import PerformanceEngine
from recovery.engine import RecoveryEngine
from renderers.morning_renderer import MorningRenderer
from repositories.health_repository import HealthRepository
from repositories.workout_repository import WorkoutRepository


def main():

    health_repository = HealthRepository()

    context = ContextBuilder().build(
        health_repository.load_daily()
    )

    health = HealthEngine().analyze(context)

    recovery = RecoveryEngine().analyze(context)

    performance = PerformanceEngine().analyze()

    last_workout = WorkoutRepository().last()

    athlete = AthleteStateBuilder().build(

        health=health,

        context=context,

        recovery=recovery,

        performance=performance,

        workout=None,

    )

    decision = DecisionEngine().decide(athlete)

    athlete.decision = decision

    print()
    print("=" * 72)
    print("ATHLETE PLATFORM")
    print("=" * 72)
    print()

    MorningRenderer().render(
        recovery=recovery,
        performance=performance,
        last_workout=last_workout,
        context=context,
        decision=decision,
    )

    print("=" * 72)
    print()


if __name__ == "__main__":
    main()