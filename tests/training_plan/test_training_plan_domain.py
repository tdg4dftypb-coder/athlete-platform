"""Unit tests for training_plan/ domain models, invariants, selector, and dependency boundaries."""
from datetime import date, datetime, timedelta, timezone
import pytest

from training_plan.models import (
    PlannedSession,
    PlannedSessionKind,
    TrainingPlan,
)
from training_plan.selector import TrainingPlanSessionSelector
from training_plan.ports import TrainingPlanProvider


def test_valid_training_session_creation():
    s = PlannedSession(
        session_id="s1",
        date=date(2026, 8, 7),
        kind=PlannedSessionKind.TRAINING,
        session_type="endurance",
        duration_minutes=90,
        target_tss=65.0,
        intensity="MODERATE",
        priority=3,
        rationale=("Aerobic base build",),
    )
    assert s.session_id == "s1"
    assert s.kind == PlannedSessionKind.TRAINING
    assert s.session_type == "ENDURANCE"  # Normalized to UPPERCASE
    assert s.duration_minutes == 90
    assert s.target_tss == 65.0
    assert s.intensity == "MODERATE"
    assert s.priority == 3
    assert s.rationale == ("Aerobic base build",)


def test_valid_rest_session_creation():
    s = PlannedSession(
        session_id="r1",
        date=date(2026, 8, 8),
        kind=PlannedSessionKind.REST,
        session_type=None,
        duration_minutes=0,
        target_tss=None,
        intensity=None,
        priority=1,
        rationale=("Scheduled recovery day",),
    )
    assert s.kind == PlannedSessionKind.REST
    assert s.session_type is None
    assert s.duration_minutes == 0
    assert s.target_tss == 0.0  # Canonical 0.0 representation for REST
    assert s.intensity is None


def test_planned_session_invalid_invariants():
    # Empty session_id
    with pytest.raises(ValueError, match="session_id"):
        PlannedSession(" ", date(2026, 8, 7), PlannedSessionKind.TRAINING, "ENDURANCE", 60, 50.0, None, 1, ())

    # datetime passed instead of date
    with pytest.raises(TypeError, match="date must be a date instance"):
        PlannedSession("s1", datetime(2026, 8, 7, 10, 0), PlannedSessionKind.TRAINING, "ENDURANCE", 60, 50.0, None, 1, ())

    # TRAINING without session_type
    with pytest.raises(ValueError, match="TRAINING session_type must be non-empty string"):
        PlannedSession("s1", date(2026, 8, 7), PlannedSessionKind.TRAINING, None, 60, 50.0, None, 1, ())

    # TRAINING with duration 0
    with pytest.raises(ValueError, match="TRAINING duration_minutes must be > 0"):
        PlannedSession("s1", date(2026, 8, 7), PlannedSessionKind.TRAINING, "ENDURANCE", 0, 50.0, None, 1, ())

    # REST with session_type
    with pytest.raises(ValueError, match="REST session_type must be None"):
        PlannedSession("r1", date(2026, 8, 7), PlannedSessionKind.REST, "RECOVERY", 0, 0.0, None, 1, ())

    # REST with duration > 0
    with pytest.raises(ValueError, match="REST duration_minutes must be 0"):
        PlannedSession("r1", date(2026, 8, 7), PlannedSessionKind.REST, None, 30, 0.0, None, 1, ())

    # Negative TSS
    with pytest.raises(ValueError, match="target_tss cannot be negative"):
        PlannedSession("s1", date(2026, 8, 7), PlannedSessionKind.TRAINING, "ENDURANCE", 60, -10.0, None, 1, ())

    # Priority out of range
    with pytest.raises(ValueError, match="priority must be bounded"):
        PlannedSession("s1", date(2026, 8, 7), PlannedSessionKind.TRAINING, "ENDURANCE", 60, 50.0, None, 6, ())


def test_valid_training_plan_creation():
    d1 = date(2026, 8, 7)
    d2 = date(2026, 8, 8)
    s1 = PlannedSession("s1", d1, PlannedSessionKind.TRAINING, "ENDURANCE", 90, 60.0, None, 3, ("Build",))
    s2 = PlannedSession("s2", d2, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",))

    plan = TrainingPlan(
        plan_id="plan-1",
        start_date=d1,
        end_date=d2,
        version=1,
        generated_at=datetime.now(timezone.utc),
        sessions=(s1, s2),
    )

    assert plan.plan_id == "plan-1"
    assert plan.version == 1
    assert len(plan.sessions) == 2
    assert plan.supersedes_plan_id is None


def test_training_plan_invariants():
    d1 = date(2026, 8, 7)
    d2 = date(2026, 8, 8)
    s1 = PlannedSession("s1", d1, PlannedSessionKind.TRAINING, "ENDURANCE", 90, 60.0, None, 3, ())
    s2 = PlannedSession("s2", d2, PlannedSessionKind.REST, None, 0, None, None, 1, ())

    # start_date > end_date
    with pytest.raises(ValueError, match="start_date must be <= end_date"):
        TrainingPlan("p1", d2, d1, 1, datetime.now(timezone.utc), (s1, s2))

    # version < 1
    with pytest.raises(ValueError, match="version must be int >= 1"):
        TrainingPlan("p1", d1, d2, 0, datetime.now(timezone.utc), (s1, s2))

    # Duplicate session_id
    s2_dup_id = PlannedSession("s1", d2, PlannedSessionKind.REST, None, 0, None, None, 1, ())
    with pytest.raises(ValueError, match="duplicate session_id"):
        TrainingPlan("p1", d1, d2, 1, datetime.now(timezone.utc), (s1, s2_dup_id))

    # Duplicate date
    s2_dup_date = PlannedSession("s2", d1, PlannedSessionKind.REST, None, 0, None, None, 1, ())
    with pytest.raises(ValueError, match="duplicate date"):
        TrainingPlan("p1", d1, d2, 1, datetime.now(timezone.utc), (s1, s2_dup_date))

    # Out of chronological order
    with pytest.raises(ValueError, match="strict chronological order"):
        TrainingPlan("p1", d1, d2, 1, datetime.now(timezone.utc), (s2, s1))

    # Missing date in range (gapless requirement)
    d3 = date(2026, 8, 9)
    with pytest.raises(ValueError, match="requires exactly 3 sessions"):
        TrainingPlan("p1", d1, d3, 1, datetime.now(timezone.utc), (s1, s2))

    # Plan supersedes itself
    with pytest.raises(ValueError, match="plan cannot supersede itself"):
        TrainingPlan("p1", d1, d2, 1, datetime.now(timezone.utc), (s1, s2), supersedes_plan_id="p1")


def test_training_plan_session_selector():
    d1 = date(2026, 8, 7)
    d2 = date(2026, 8, 8)
    d3 = date(2026, 8, 9)
    s1 = PlannedSession("s1", d1, PlannedSessionKind.TRAINING, "ENDURANCE", 90, 60.0, None, 3, ())
    s2 = PlannedSession("s2", d2, PlannedSessionKind.REST, None, 0, None, None, 1, ())
    s3 = PlannedSession("s3", d3, PlannedSessionKind.TRAINING, "VO2", 60, 75.0, None, 4, ())

    plan = TrainingPlan("p1", d1, d3, 1, datetime.now(timezone.utc), (s1, s2, s3))
    selector = TrainingPlanSessionSelector()

    # Match first, middle (REST), and last
    res_d1 = selector.get_for_date(plan, d1)
    assert res_d1 == s1
    assert res_d1.kind == PlannedSessionKind.TRAINING

    res_d2 = selector.get_for_date(plan, d2)
    assert res_d2 == s2
    assert res_d2.kind == PlannedSessionKind.REST

    res_d3 = selector.get_for_date(plan, d3)
    assert res_d3 == s3
    assert res_d3.kind == PlannedSessionKind.TRAINING

    # Out of range date returns None
    assert selector.get_for_date(plan, date(2026, 8, 6)) is None
    assert selector.get_for_date(plan, date(2026, 8, 10)) is None


def test_training_plan_dependency_boundary():
    """Verifies training_plan module has no forbidden external imports."""
    import sys
    import training_plan

    forbidden = {"decision", "recovery", "biomarkers", "performance", "morning_briefing", "workout"}
    for mod_name in sys.modules:
        if mod_name.startswith("training_plan.") or mod_name == "training_plan":
            mod = sys.modules[mod_name]
            for attr in dir(mod):
                val = getattr(mod, attr)
                val_mod = getattr(val, "__module__", "")
                for f in forbidden:
                    assert not val_mod.startswith(f), f"Forbidden import of '{f}' found in training_plan"


def test_training_plan_provider_protocol_contract():
    class DummyProvider:
        def get_plan_for_date(self, target_date: date) -> TrainingPlan | None:
            return None

        def get_planned_session(self, target_date: date) -> PlannedSession | None:
            return None

    dummy = DummyProvider()
    assert isinstance(dummy, TrainingPlanProvider)
