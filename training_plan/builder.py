"""Stateless builder for projecting a TrainingIntent onto a calendar range to construct a TrainingPlan."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from training_plan.intent import TrainingIntent
from training_plan.models import PlannedSession, TrainingPlan


class BaselineTrainingPlanBuilder:
    """Stateless builder projecting a TrainingIntent onto a calendar range [start_date, end_date]."""

    def build(
        self,
        intent: TrainingIntent,
        start_date: date,
        end_date: date,
        plan_id: str,
        generated_at: datetime,
        version: int = 1,
        supersedes_plan_id: str | None = None,
    ) -> TrainingPlan:
        """Projects TrainingIntent onto [start_date, end_date] and constructs immutable TrainingPlan.

        Generates deterministic session IDs in format: {plan_id}:{YYYY-MM-DD}
        """
        if not isinstance(intent, TrainingIntent):
            raise TypeError("intent must be TrainingIntent instance")

        if type(start_date) is not date:
            raise TypeError("start_date must be date instance")
        if type(end_date) is not date:
            raise TypeError("end_date must be date instance")
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime instance")

        # Map Monday(0)..Sunday(6) to WeeklySessionIntent
        weekday_map = {item.weekday.value: item for item in intent.weekly_sessions}

        sessions: list[PlannedSession] = []
        curr_date = start_date
        one_day = timedelta(days=1)

        while curr_date <= end_date:
            w_intent = weekday_map[curr_date.weekday()]
            session_id = f"{plan_id}:{curr_date.isoformat()}"

            planned_session = PlannedSession(
                session_id=session_id,
                date=curr_date,
                kind=w_intent.kind,
                session_type=w_intent.session_type,
                duration_minutes=w_intent.duration_minutes,
                target_tss=w_intent.target_tss,
                intensity=w_intent.intensity,
                priority=w_intent.priority,
                rationale=w_intent.rationale,
            )
            sessions.append(planned_session)
            curr_date += one_day

        return TrainingPlan(
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
            version=version,
            generated_at=generated_at,
            sessions=tuple(sessions),
            supersedes_plan_id=supersedes_plan_id,
        )
