from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

from scripts import export_workout
from workout.enums import WorkoutType


@dataclass
class DecisionResultFixture:
    recommendation: WorkoutType


def test_main_builds_athlete_state_with_health_and_context(monkeypatch):
    history = [object()]
    context = object()
    health = object()
    recovery = object()
    performance = object()
    activity = object()
    summary = object()
    athlete = object()
    decision_result = DecisionResultFixture(WorkoutType.ENDURANCE)
    decision = SimpleNamespace(decision=decision_result)
    workout = object()
    metrics = SimpleNamespace(
        duration=60,
        expected_if=0.7,
        expected_tss=50.0,
    )
    fit_file = object()
    exported_file = object()

    context_builder = SimpleNamespace(build=Mock(return_value=context))
    health_engine = SimpleNamespace(analyze=Mock(return_value=health))
    recovery_engine = SimpleNamespace(analyze=Mock(return_value=recovery))
    performance_engine = SimpleNamespace(analyze=Mock(return_value=performance))
    athlete_state_builder = SimpleNamespace(build=Mock(return_value=athlete))
    workout_builder = SimpleNamespace(build=Mock(return_value=workout))

    monkeypatch.setattr(
        export_workout,
        "HealthRepository",
        lambda: SimpleNamespace(load_daily=Mock(return_value=history)),
    )
    monkeypatch.setattr(export_workout, "ContextBuilder", lambda: context_builder)
    monkeypatch.setattr(export_workout, "HealthEngine", lambda: health_engine)
    monkeypatch.setattr(export_workout, "RecoveryEngine", lambda: recovery_engine)
    monkeypatch.setattr(
        export_workout,
        "PerformanceEngine",
        lambda: performance_engine,
    )
    monkeypatch.setattr(
        export_workout,
        "Path",
        lambda _: SimpleNamespace(glob=Mock(return_value=[fit_file])),
    )
    monkeypatch.setattr(
        export_workout,
        "FitParser",
        lambda: SimpleNamespace(parse=Mock(return_value=object())),
    )
    monkeypatch.setattr(
        export_workout,
        "ActivityFactory",
        lambda: SimpleNamespace(create=Mock(return_value=activity)),
    )
    monkeypatch.setattr(
        export_workout,
        "WorkoutAnalyzer",
        lambda: SimpleNamespace(analyze=Mock(return_value=summary)),
    )
    monkeypatch.setattr(
        export_workout,
        "AthleteStateBuilder",
        lambda: athlete_state_builder,
    )
    monkeypatch.setattr(
        export_workout,
        "DecisionEngine",
        lambda: SimpleNamespace(decide=Mock(return_value=decision)),
    )
    monkeypatch.setattr(
        export_workout,
        "WorkoutBuilder",
        lambda: workout_builder,
    )
    monkeypatch.setattr(
        export_workout,
        "WorkoutCalculator",
        lambda: SimpleNamespace(calculate=Mock(return_value=metrics)),
    )
    monkeypatch.setattr(
        export_workout,
        "ZwoExporter",
        lambda: SimpleNamespace(export=Mock(return_value=exported_file)),
    )

    export_workout.main()

    context_builder.build.assert_called_once_with(history)
    health_engine.analyze.assert_called_once_with(context)
    recovery_engine.analyze.assert_called_once_with(context)
    athlete_state_builder.build.assert_called_once_with(
        health=health,
        context=context,
        recovery=recovery,
        performance=performance,
        workout=summary,
    )
    legacy_decision = workout_builder.build.call_args.args[0]
    assert legacy_decision is not decision_result
    assert legacy_decision.recommendation == "ENDURANCE"
