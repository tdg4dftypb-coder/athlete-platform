"""Unit tests for Stage 26.2 intent models, baseline builder, determinism, and boundaries."""
from datetime import date, datetime, timedelta, timezone
import pytest

from training_plan.builder import BaselineTrainingPlanBuilder
from training_plan.intent import (
    TrainingIntent,
    Weekday,
    WeeklySessionIntent,
)
from training_plan.models import (
    PlannedSession,
    PlannedSessionKind,
    TrainingPlan,
)


def build_generic_test_intent(intent_id="generic-intent-01") -> TrainingIntent:
    """Helper creating generic 7-day WeeklySessionIntent without personal schedules."""
    m = WeeklySessionIntent(Weekday.MONDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest Monday",))
    t = WeeklySessionIntent(Weekday.TUESDAY, PlannedSessionKind.TRAINING, "VO2", 60, 70.0, "HIGH", 4, ("Intervals",))
    w = WeeklySessionIntent(Weekday.WEDNESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest Wednesday",))
    r = WeeklySessionIntent(Weekday.THURSDAY, PlannedSessionKind.TRAINING, "ENDURANCE", 90, 60.0, "MODERATE", 3, ("Base",))
    f = WeeklySessionIntent(Weekday.FRIDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest Friday",))
    s = WeeklySessionIntent(Weekday.SATURDAY, PlannedSessionKind.TRAINING, "THRESHOLD", 75, 80.0, "HIGH", 4, ("FTP",))
    u = WeeklySessionIntent(Weekday.SUNDAY, PlannedSessionKind.TRAINING, "ENDURANCE", 120, 90.0, "MODERATE", 3, ("Long Ride",))

    return TrainingIntent(intent_id, (m, t, w, r, f, s, u))


def test_weekday_enum_mapping():
    assert Weekday.MONDAY.value == 0 == date(2026, 8, 10).weekday()
    assert Weekday.TUESDAY.value == 1 == date(2026, 8, 11).weekday()
    assert Weekday.WEDNESDAY.value == 2 == date(2026, 8, 12).weekday()
    assert Weekday.THURSDAY.value == 3 == date(2026, 8, 13).weekday()
    assert Weekday.FRIDAY.value == 4 == date(2026, 8, 14).weekday()
    assert Weekday.SATURDAY.value == 5 == date(2026, 8, 15).weekday()
    assert Weekday.SUNDAY.value == 6 == date(2026, 8, 16).weekday()


def test_weekly_session_intent_training_and_rest():
    tr = WeeklySessionIntent(
        weekday=Weekday.TUESDAY,
        kind=PlannedSessionKind.TRAINING,
        session_type="tempo",
        duration_minutes=60,
        target_tss=50.0,
        intensity="moderate",
        priority=3,
        rationale=("Tempo work",),
    )
    assert tr.session_type == "TEMPO"
    assert tr.intensity == "MODERATE"
    assert tr.duration_minutes == 60

    rest = WeeklySessionIntent(
        weekday=Weekday.MONDAY,
        kind=PlannedSessionKind.REST,
        session_type=None,
        duration_minutes=0,
        target_tss=None,
        intensity=None,
        priority=1,
        rationale=("Rest day",),
    )
    assert rest.target_tss == 0.0
    assert rest.session_type is None


def test_training_intent_canonicalization_and_validation():
    intent = build_generic_test_intent("intent-01")
    assert intent.intent_id == "intent-01"
    assert len(intent.weekly_sessions) == 7
    # Canonical order Monday (0) -> Sunday (6)
    for idx, sess in enumerate(intent.weekly_sessions):
        assert sess.weekday.value == idx

    # Duplicate weekday error
    m1 = WeeklySessionIntent(Weekday.MONDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R1",))
    m2 = WeeklySessionIntent(Weekday.MONDAY, PlannedSessionKind.TRAINING, "VO2", 60, 50.0, None, 2, ("T1",))
    t = WeeklySessionIntent(Weekday.TUESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R2",))
    w = WeeklySessionIntent(Weekday.WEDNESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R3",))
    r = WeeklySessionIntent(Weekday.THURSDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R4",))
    f = WeeklySessionIntent(Weekday.FRIDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R5",))
    s = WeeklySessionIntent(Weekday.SATURDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R6",))

    with pytest.raises(ValueError, match="duplicate weekday"):
        TrainingIntent("invalid-intent", (m1, m2, t, w, r, f, s))

    # Missing weekday error (only 6 sessions)
    with pytest.raises(ValueError, match="requires exactly 7 weekly sessions"):
        TrainingIntent("invalid-intent", (m1, t, w, r, f, s))

    # Empty intent_id error
    u = WeeklySessionIntent(Weekday.SUNDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("R7",))
    with pytest.raises(ValueError, match="intent_id"):
        TrainingIntent(" ", (m1, t, w, r, f, s, u))


def test_builder_single_day_and_seven_day_projection():
    builder = BaselineTrainingPlanBuilder()
    intent = build_generic_test_intent("intent-proj")

    t_gen = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    d_start = date(2026, 8, 10)  # Monday
    d_end = date(2026, 8, 16)    # Sunday

    plan = builder.build(
        intent=intent,
        start_date=d_start,
        end_date=d_end,
        plan_id="plan-baseline-1",
        generated_at=t_gen,
        version=1,
        supersedes_plan_id=None,
    )

    assert isinstance(plan, TrainingPlan)
    assert plan.plan_id == "plan-baseline-1"
    assert len(plan.sessions) == 7
    assert plan.sessions[0].session_id == "plan-baseline-1:2026-08-10"
    assert plan.sessions[0].kind == PlannedSessionKind.REST
    assert plan.sessions[1].session_id == "plan-baseline-1:2026-08-11"
    assert plan.sessions[1].kind == PlannedSessionKind.TRAINING
    assert plan.sessions[1].session_type == "VO2"


def test_builder_partial_week_multi_week_month_year_boundary():
    builder = BaselineTrainingPlanBuilder()
    intent = build_generic_test_intent("intent-boundaries")
    t_gen = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Partial week: Wednesday to Friday (3 days)
    p_part = builder.build(
        intent=intent,
        start_date=date(2026, 8, 12),  # Wednesday
        end_date=date(2026, 8, 14),    # Friday
        plan_id="plan-part",
        generated_at=t_gen,
    )
    assert len(p_part.sessions) == 3
    assert p_part.sessions[0].date == date(2026, 8, 12)
    assert p_part.sessions[0].kind == PlannedSessionKind.REST
    assert p_part.sessions[2].date == date(2026, 8, 14)

    # 2. Multi-week across month boundary: Aug 24 to Sep 6 (14 days)
    p_multi = builder.build(
        intent=intent,
        start_date=date(2026, 8, 24),
        end_date=date(2026, 9, 6),
        plan_id="plan-multi",
        generated_at=t_gen,
    )
    assert len(p_multi.sessions) == 14
    assert p_multi.sessions[0].date == date(2026, 8, 24)
    assert p_multi.sessions[13].date == date(2026, 9, 6)

    # 3. Year boundary: Dec 28, 2026 to Jan 3, 2027 (7 days)
    p_year = builder.build(
        intent=intent,
        start_date=date(2026, 12, 28),
        end_date=date(2027, 1, 3),
        plan_id="plan-year",
        generated_at=t_gen,
    )
    assert len(p_year.sessions) == 7
    assert p_year.sessions[0].session_id == "plan-year:2026-12-28"
    assert p_year.sessions[6].session_id == "plan-year:2027-01-03"


def test_builder_determinism_and_version_forwarding():
    builder = BaselineTrainingPlanBuilder()
    intent = build_generic_test_intent("intent-det")
    t_gen = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)

    p1 = builder.build(
        intent=intent,
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-v2",
        generated_at=t_gen,
        version=2,
        supersedes_plan_id="plan-v1",
    )

    p2 = builder.build(
        intent=intent,
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-v2",
        generated_at=t_gen,
        version=2,
        supersedes_plan_id="plan-v1",
    )

    assert p1 == p2
    assert p1.version == 2
    assert p1.supersedes_plan_id == "plan-v1"


def test_builder_invalid_inputs_error_handling():
    builder = BaselineTrainingPlanBuilder()
    intent = build_generic_test_intent("intent-err")
    t_gen = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)

    # start_date > end_date
    with pytest.raises(ValueError, match="start_date must be <= end_date"):
        builder.build(intent, date(2026, 8, 16), date(2026, 8, 10), "p1", t_gen)

    # datetime instead of date
    with pytest.raises(TypeError, match="start_date must be date instance"):
        builder.build(intent, datetime(2026, 8, 10), date(2026, 8, 16), "p1", t_gen)

    # Empty plan_id
    with pytest.raises(ValueError, match="plan_id"):
        builder.build(intent, date(2026, 8, 10), date(2026, 8, 16), " ", t_gen)


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
                    assert not val_mod.startswith(f), f"Forbidden import of '{f}' found in training_plan: {attr}"
