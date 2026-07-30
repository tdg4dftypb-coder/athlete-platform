from datetime import datetime, time, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application import (
    AdaptationPolicy,
    AthleteAssessmentBuilder,
    AthleteKnowledgeContextBuilder,
    MorningCoachBuilder,
    MorningCoachReport,
    TrainingAssessmentBuilder,
    WeeklyReviewWorkflow,
)
from athlete.memory import (
    AthleteMemoryReader,
    AthleteMemoryRepository,
    DateRange,
    PatternDetector,
    TrendEngine,
)
from athlete.review import WeeklyReviewService
from athlete.state_builder import AthleteStateBuilder
from core.database import Database
from decision.engine import DecisionEngine
from engines.context_builder import ContextBuilder
from health.engine import HealthEngine
from performance.engine import PerformanceEngine
from planner.engine import PlannerEngine
from recovery.engine import RecoveryEngine
from repositories.health_repository import HealthRepository
from schema.athlete_memory_schema import AthleteMemorySchema


def build_report() -> MorningCoachReport:
    """Run the existing deterministic AI Coach workflow for the current day."""

    health_repository = HealthRepository()
    health_context = ContextBuilder().build(health_repository.load_daily())
    health = HealthEngine().analyze(health_context)
    recovery = RecoveryEngine().analyze(health_context)
    performance = PerformanceEngine().analyze()
    athlete = AthleteStateBuilder().build(
        health=health,
        context=health_context,
        recovery=recovery,
        performance=performance,
    )

    as_of = datetime.combine(health_context.today.date, time.min)
    period = DateRange(
        start=as_of - timedelta(days=6),
        end=as_of + timedelta(days=1),
    )

    database = Database()
    try:
        AthleteMemorySchema(database).create()
        weekly_review = WeeklyReviewWorkflow(
            reader=AthleteMemoryReader(AthleteMemoryRepository(database)),
            trend_engine=TrendEngine(),
            pattern_detector=PatternDetector(),
            review_service=WeeklyReviewService(),
        ).run(period)
    finally:
        database.close()

    knowledge_context = AthleteKnowledgeContextBuilder().build(
        as_of=as_of,
        athlete_state=athlete,
        weekly_review=weekly_review,
    )
    training_assessment = TrainingAssessmentBuilder().build(knowledge_context)
    athlete_assessment = AthleteAssessmentBuilder().build(
        knowledge_context,
        training_assessment,
    )
    adaptation = AdaptationPolicy().evaluate(athlete_assessment)
    plan = DecisionEngine().decide(athlete, adaptation)
    workout = PlannerEngine().build(plan.decision, athlete)

    return MorningCoachBuilder().build(
        athlete,
        athlete_assessment,
        adaptation,
        workout,
    )


def render(report: MorningCoachReport) -> None:
    print("=" * 41)
    print("AI COACH")
    print("=" * 41)
    print()
    print("Status:")
    print(report.athlete_assessment.status.value)
    print()
    print("Today's workout:")
    print(report.workout.name)
    print()
    print("Explanation:")
    print(report.explanation.summary)
    print()
    print("Reasons:")
    for reason in report.explanation.reasons:
        print(f"- {reason}")
    print()
    print("=" * 41)


def main() -> None:
    render(build_report())


if __name__ == "__main__":
    main()
