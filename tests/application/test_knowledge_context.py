from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from inspect import signature

import pytest

from application import AthleteKnowledgeContext, AthleteKnowledgeContextBuilder
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    DateRange,
)
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.trends import TrendEngine
from athlete.review.weekly import WeeklyReviewService
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema
from tests.helpers import build_athlete


def build_period() -> DateRange:

    start = datetime(2026, 8, 1)
    return DateRange(start=start, end=start + timedelta(days=7))


def build_event(period: DateRange) -> AthleteMemoryEvent:

    return AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=period.start + timedelta(hours=1),
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="activity-1",
        schema_version=1,
        payload={
            "schema_version": 1,
            "execution": {
                "planned_duration": 60,
                "executed_duration": 60,
                "planned_tss": 100,
                "executed_tss": 100,
                "completion_score": 0.95,
                "execution_score": 0.95,
                "completed": True,
            },
            "feedback": {"status": "completed"},
        },
    )


def test_knowledge_context_is_frozen_and_preserves_exact_references():

    as_of = datetime(2026, 8, 7, 12, 0)
    athlete_state = build_athlete()
    builder = AthleteKnowledgeContextBuilder()

    context = builder.build(
        as_of=as_of,
        athlete_state=athlete_state,
    )

    assert context.as_of is as_of
    assert context.athlete_state is athlete_state
    assert context.weekly_review is None

    with pytest.raises(FrozenInstanceError):
        context.as_of = datetime(2026, 8, 8)


def test_knowledge_context_accepts_no_optional_sections():

    as_of = datetime(2026, 8, 7, 12, 0)

    context = AthleteKnowledgeContextBuilder().build(as_of=as_of)

    assert context == AthleteKnowledgeContext(
        as_of=as_of,
        athlete_state=None,
        weekly_review=None,
    )


def test_knowledge_context_accepts_a_review_without_athlete_state():

    db = Database(":memory:")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    period = build_period()
    repository.append(build_event(period))
    review = WeeklyReviewWorkflow(
        AthleteMemoryReader(repository),
        TrendEngine(),
        PatternDetector(),
        WeeklyReviewService(),
    ).run(period)
    as_of = datetime(2026, 8, 7, 12, 0)

    context = AthleteKnowledgeContextBuilder().build(
        as_of=as_of,
        weekly_review=review,
    )

    assert context.athlete_state is None
    assert context.weekly_review is review
    assert context.weekly_review.period is period
    assert context.weekly_review.source_event_ids == ("event-1",)

    db.close()


def test_knowledge_context_build_is_deterministic():

    as_of = datetime(2026, 8, 7, 12, 0)
    athlete_state = build_athlete()
    builder = AthleteKnowledgeContextBuilder()

    first = builder.build(as_of=as_of, athlete_state=athlete_state)
    second = builder.build(as_of=as_of, athlete_state=athlete_state)

    assert first == second
    assert first.athlete_state is athlete_state
    assert second.athlete_state is athlete_state


def test_knowledge_context_builder_has_no_constructor_dependencies():

    assert tuple(signature(AthleteKnowledgeContextBuilder).parameters) == ()
