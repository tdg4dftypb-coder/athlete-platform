from dataclasses import replace
from datetime import date, datetime, timedelta
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
    TrainingAssessmentBuilder,
)
from athlete.memory.models import DateRange, PatternReport, TrainingTrendReport
from athlete.models import AthleteState
from athlete.review.models import WeeklyTrainingReview
from core.context import HealthContext
from core.models import HealthDaily
from decision.engine import DecisionEngine
from engines.trend_engine import TrendMetric
from health.models import HealthState
from performance.models import PerformanceState
from performance.training_load import TrainingLoad
from planner.engine import PlannerEngine
from recovery.models import RecoveryMetric, RecoveryResult
from workout.builder import WorkoutBuilder

AS_OF = datetime(2026, 8, 7, 12, 0)


def _trend(value: float) -> TrendMetric:
    return TrendMetric(
        today=value,
        average_7=value,
        average_30=value,
        delta=0,
        delta_percent=0,
    )


def _athlete(
    recovery_score: int,
    fatigue: float,
) -> AthleteState:
    trend = _trend(1)
    health_context = HealthContext(
        today=HealthDaily(
            date=date(2026, 8, 7),
            hrv=70,
            resting_hr=45,
            sleep_duration=480,
        ),
        hrv=_trend(70),
        resting_hr=_trend(45),
        sleep=_trend(480),
    )
    health = HealthState(
        weight=trend,
        hrv=trend,
        resting_hr=trend,
        sleep=trend,
        steps=trend,
    )
    recovery_metric = RecoveryMetric(
        value=0,
        baseline=0,
        delta=0,
        delta_percent=0,
        score=recovery_score,
    )
    recovery = RecoveryResult(
        score=recovery_score,
        status="OK",
        reasons=[],
        hrv=recovery_metric,
        resting_hr=recovery_metric,
        sleep=recovery_metric,
    )
    training_load = TrainingLoad(
        total_tss=0,
        average_tss=0,
        workouts=0,
        average_daily_tss=0,
        period_days=7,
    )
    performance = PerformanceState(
        weekly=training_load,
        monthly=training_load,
        atl=0,
        ctl=0,
        tsb=0,
        fatigue=fatigue,
        fitness=0,
        freshness=0,
    )

    return AthleteState(
        health=health,
        context=health_context,
        recovery=recovery,
        performance=performance,
    )


def _weekly_review() -> WeeklyTrainingReview:
    period = DateRange(
        start=AS_OF - timedelta(days=7),
        end=AS_OF,
    )
    trends = TrainingTrendReport(
        period=period,
        workouts_count=1,
        planned_duration=60,
        executed_duration=60,
        planned_tss=50,
        executed_tss=50,
        average_completion_score=100,
        average_execution_score=100,
    )
    patterns = PatternReport(
        period=period,
        patterns=(),
        source_event_ids=(),
    )

    return WeeklyTrainingReview(
        period=period,
        trends=trends,
        patterns=patterns,
        source_event_ids=(),
    )


def run_scenario(
    title: str,
    *,
    recovery_score: int,
    fatigue: float,
    has_training_data: bool,
) -> None:
    athlete = _athlete(recovery_score, fatigue)
    knowledge_context = AthleteKnowledgeContextBuilder().build(
        as_of=AS_OF,
        athlete_state=athlete,
        weekly_review=_weekly_review() if has_training_data else None,
    )
    training = TrainingAssessmentBuilder().build(knowledge_context)
    assessment = AthleteAssessmentBuilder().build(knowledge_context, training)
    adaptation = AdaptationPolicy().evaluate(assessment)
    plan = DecisionEngine().decide(athlete, adaptation)
    workout = PlannerEngine().build(plan.decision, athlete)
    report = MorningCoachBuilder().build(
        athlete,
        assessment,
        adaptation,
        workout,
    )
    legacy_workout = WorkoutBuilder().build(
        replace(
            plan.decision,
            recommendation=plan.decision.recommendation.name,
        ),
    )

    print("=" * 41)
    print(title)
    print("=" * 41)
    print(f"Morning Coach status: {report.athlete_assessment.status.value}")
    print(f"Adaptation directive: {report.adaptation.status.value}")
    print(f"Today's workout: {report.workout.name}")
    print(f"Explanation: {report.explanation.summary}")
    print("Reasons:")
    for reason in report.explanation.reasons:
        print(f"- {reason}")
    print(
        "WorkoutBuilder output: "
        f"{legacy_workout.name} ({len(legacy_workout.blocks)} blocks)",
    )
    print()


def main() -> None:
    run_scenario(
        "INSUFFICIENT_DATA",
        recovery_score=70,
        fatigue=79,
        has_training_data=False,
    )
    run_scenario(
        "REDUCE_LOAD",
        recovery_score=69,
        fatigue=79,
        has_training_data=True,
    )
    run_scenario(
        "MAINTAIN",
        recovery_score=70,
        fatigue=79,
        has_training_data=True,
    )


if __name__ == "__main__":
    main()
