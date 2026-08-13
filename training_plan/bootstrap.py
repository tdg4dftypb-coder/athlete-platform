"""Operator-supplied specification adapter for initial Training Plan bootstrap."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json

from training_plan.builder import BaselineTrainingPlanBuilder
from training_plan.intent import TrainingIntent, Weekday, WeeklySessionIntent
from training_plan.models import PlannedSessionKind, TrainingPlan
from training_plan.continuity import (
    ContinuationSessionSlot, ContinuationWeekday, TrainingPlanContinuationSpecification,
)


BOOTSTRAP_SCHEMA_VERSION = "1.0"


class TrainingPlanBootstrapSpecificationError(ValueError):
    pass


@dataclass(frozen=True)
class TrainingPlanBootstrapSpecification:
    intent: TrainingIntent
    plan_id: str
    start_date: date
    end_date: date
    generated_at_utc: datetime
    version: int
    supersedes_plan_id: str | None = None
    schema_version: str = BOOTSTRAP_SCHEMA_VERSION

    def build_plan(self) -> TrainingPlan:
        return BaselineTrainingPlanBuilder().build(
            intent=self.intent,
            start_date=self.start_date,
            end_date=self.end_date,
            plan_id=self.plan_id,
            generated_at=self.generated_at_utc,
            version=self.version,
            supersedes_plan_id=self.supersedes_plan_id,
        )

    def build_continuation_specification(self, *, specification_id: str, version: int,
                                         target_horizon_days: int, extension_days: int, created_at: datetime):
        days=tuple(ContinuationWeekday(item.weekday,(ContinuationSessionSlot(
            f"{item.weekday.name.lower()}-primary",item.kind,item.session_type,item.duration_minutes,
            item.target_tss,item.intensity,item.priority,item.rationale),)) for item in self.intent.weekly_sessions)
        return TrainingPlanContinuationSpecification.create(
            specification_id,version,self.plan_id,target_horizon_days,extension_days,days,created_at)


def parse_bootstrap_specification(payload: str) -> TrainingPlanBootstrapSpecification:
    """Parse explicit JSON and delegate schedule validation to existing domain models."""
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise TypeError("root must be an object")
        if data["schema_version"] != BOOTSTRAP_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version '{data['schema_version']}'")
        raw_sessions = data["weekly_sessions"]
        if not isinstance(raw_sessions, list):
            raise TypeError("weekly_sessions must be a list")
        sessions = tuple(
            WeeklySessionIntent(
                weekday=Weekday[item["weekday"]],
                kind=PlannedSessionKind(item["kind"]),
                session_type=item["session_type"],
                duration_minutes=item["duration_minutes"],
                target_tss=item["target_tss"],
                intensity=item["intensity"],
                priority=item["priority"],
                rationale=tuple(item["rationale"]),
            )
            for item in raw_sessions
        )
        generated_at = datetime.fromisoformat(data["generated_at_utc"].replace("Z", "+00:00"))
        if generated_at.tzinfo is None or generated_at.utcoffset() != timezone.utc.utcoffset(generated_at):
            raise ValueError("generated_at_utc must be timezone-aware UTC")
        specification = TrainingPlanBootstrapSpecification(
            schema_version=data["schema_version"],
            intent=TrainingIntent(data["intent_id"], sessions),
            plan_id=data["plan_id"],
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            generated_at_utc=generated_at,
            version=data["version"],
            supersedes_plan_id=data.get("supersedes_plan_id"),
        )
        specification.build_plan()
        return specification
    except TrainingPlanBootstrapSpecificationError:
        raise
    except Exception as error:
        raise TrainingPlanBootstrapSpecificationError(
            f"Invalid Training Plan bootstrap specification: {error}"
        ) from error
