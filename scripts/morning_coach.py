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
    MorningCoachUseCase,
    TrainingAssessmentBuilder,
    WeeklyReviewWorkflow,
)
from athlete.memory import (
    AthleteMemoryReader,
    AthleteMemoryRepository,
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


def build_report() -> MorningCoachReport:
    """Run the existing deterministic AI Coach workflow for the current day."""

    database = Database()
    try:
        use_case = MorningCoachUseCase(
            health_repository=HealthRepository(),
            context_builder=ContextBuilder(),
            health_engine=HealthEngine(),
            recovery_engine=RecoveryEngine(),
            performance_engine=PerformanceEngine(),
            athlete_state_builder=AthleteStateBuilder(),
            weekly_review_workflow=WeeklyReviewWorkflow(
                reader=AthleteMemoryReader(AthleteMemoryRepository(database)),
                trend_engine=TrendEngine(),
                pattern_detector=PatternDetector(),
                review_service=WeeklyReviewService(),
            ),
            knowledge_context_builder=AthleteKnowledgeContextBuilder(),
            training_assessment_builder=TrainingAssessmentBuilder(),
            athlete_assessment_builder=AthleteAssessmentBuilder(),
            adaptation_policy=AdaptationPolicy(),
            decision_engine=DecisionEngine(),
            planner_engine=PlannerEngine(),
            morning_coach_builder=MorningCoachBuilder(),
        )
        return use_case.run().report
    finally:
        database.close()


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
