"""Tests for LactateCurve, LactateCurvePoint, and LactateCurveBuilder — Sprint 21.3."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

import performance_lab
from performance_lab.domain import (
    ExerciseModality,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.lactate_curve import (
    LactateCurve,
    LactateCurveBuilder,
    LactateCurvePoint,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

NOW = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)
BUILDER = LactateCurveBuilder()


def make_stage(
    stage_number: int = 1,
    completion_status: StageCompletionStatus = StageCompletionStatus.COMPLETED,
    lactate_mmol_l: float | None = 1.5,
    power_watts: float | None = 150.0,
    speed_kph: float | None = 30.0,
    heart_rate_bpm: int | None = 140,
) -> PerformanceStage:
    return PerformanceStage(
        stage_number=stage_number,
        completion_status=completion_status,
        lactate_mmol_l=lactate_mmol_l,
        power_watts=power_watts,
        speed_kph=speed_kph,
        heart_rate_bpm=heart_rate_bpm,
    )


def make_session(
    stages: tuple[PerformanceStage, ...],
    test_id: str = "test-session-001",
) -> PerformanceTestSession:
    return PerformanceTestSession(
        test_id=test_id,
        performed_at=NOW,
        test_type=PerformanceTestType.LACTATE_STEP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=stages,
    )


# ── Test LactateCurveBuilder ──────────────────────────────────────────────────


class TestLactateCurveBuilder:
    def test_full_curve_multi_point(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=1.0, power_watts=150.0, heart_rate_bpm=130),
            make_stage(2, lactate_mmol_l=1.5, power_watts=200.0, heart_rate_bpm=145),
            make_stage(3, lactate_mmol_l=3.0, power_watts=250.0, heart_rate_bpm=160),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        assert curve.test_id == "test-session-001"
        assert len(curve.points) == 3
        assert isinstance(curve.points, tuple)

        p1, p2, p3 = curve.points

        # First point: changes are None
        assert p1.stage_number == 1
        assert p1.lactate_mmol_l == 1.0
        assert p1.power_watts == 150.0
        assert p1.heart_rate_bpm == 130
        assert p1.absolute_change_mmol_l is None
        assert p1.relative_change_percent is None

        # Second point: positive change
        assert p2.stage_number == 2
        assert p2.lactate_mmol_l == 1.5
        assert p2.absolute_change_mmol_l == pytest.approx(0.5)
        assert p2.relative_change_percent == pytest.approx(50.0)

        # Third point: positive change
        assert p3.stage_number == 3
        assert p3.lactate_mmol_l == 3.0
        assert p3.absolute_change_mmol_l == pytest.approx(1.5)
        assert p3.relative_change_percent == pytest.approx(100.0)

    def test_negative_changes_supported(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=2.0),
            make_stage(2, lactate_mmol_l=1.5),  # drop in lactate
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        p2 = curve.points[1]
        assert p2.absolute_change_mmol_l == pytest.approx(-0.5)
        assert p2.relative_change_percent == pytest.approx(-25.0)

    def test_previous_lactate_zero_relative_change_is_none(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=0.0),
            make_stage(2, lactate_mmol_l=1.0),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        p2 = curve.points[1]
        assert p2.absolute_change_mmol_l == pytest.approx(1.0)
        assert p2.relative_change_percent is None

    def test_no_precision_rounding(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=1.123456789),
            make_stage(2, lactate_mmol_l=2.987654321),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        p1, p2 = curve.points
        assert p1.lactate_mmol_l == 1.123456789
        assert p2.lactate_mmol_l == 2.987654321
        assert p2.absolute_change_mmol_l == 2.987654321 - 1.123456789

    def test_filter_non_completed_and_none_lactate(self) -> None:
        stages = (
            make_stage(1, completion_status=StageCompletionStatus.COMPLETED, lactate_mmol_l=1.2),
            make_stage(2, completion_status=StageCompletionStatus.INCOMPLETE, lactate_mmol_l=1.8),
            make_stage(3, completion_status=StageCompletionStatus.SKIPPED, lactate_mmol_l=2.5),
            make_stage(4, completion_status=StageCompletionStatus.COMPLETED, lactate_mmol_l=None),
            make_stage(5, completion_status=StageCompletionStatus.COMPLETED, lactate_mmol_l=3.2),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        assert len(curve.points) == 2
        assert curve.points[0].stage_number == 1
        assert curve.points[0].lactate_mmol_l == 1.2
        assert curve.points[1].stage_number == 5
        assert curve.points[1].lactate_mmol_l == 3.2
        # Delta computed between qualified stage 1 and stage 5
        assert curve.points[1].absolute_change_mmol_l == pytest.approx(2.0)

    def test_no_qualified_stages_returns_empty_points(self) -> None:
        stages = (
            make_stage(1, completion_status=StageCompletionStatus.INCOMPLETE, lactate_mmol_l=1.5),
            make_stage(2, completion_status=StageCompletionStatus.COMPLETED, lactate_mmol_l=None),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        assert curve.test_id == "test-session-001"
        assert curve.points == ()

    def test_single_qualified_stage(self) -> None:
        stages = (make_stage(1, lactate_mmol_l=1.5),)
        session = make_session(stages)
        curve = BUILDER.build(session)

        assert len(curve.points) == 1
        p1 = curve.points[0]
        assert p1.stage_number == 1
        assert p1.lactate_mmol_l == 1.5
        assert p1.absolute_change_mmol_l is None
        assert p1.relative_change_percent is None

    def test_preserves_stage_order(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=1.0),
            make_stage(2, lactate_mmol_l=1.5),
            make_stage(3, lactate_mmol_l=2.0),
        )
        session = make_session(stages)
        curve = BUILDER.build(session)

        stage_numbers = [p.stage_number for p in curve.points]
        assert stage_numbers == [1, 2, 3]

    def test_statelessness_and_idempotence(self) -> None:
        stages = (
            make_stage(1, lactate_mmol_l=1.0),
            make_stage(2, lactate_mmol_l=2.0),
        )
        session = make_session(stages)
        c1 = BUILDER.build(session)
        c2 = BUILDER.build(session)

        assert c1 == c2
        # Original session is unchanged
        assert len(session.stages) == 2


# ── Model Invariant Validation ────────────────────────────────────────────────


class TestModelValidation:
    def test_lactate_curve_point_invalid_stage_number(self) -> None:
        with pytest.raises(ValueError, match="stage_number"):
            LactateCurvePoint(stage_number=0, lactate_mmol_l=1.5)

    def test_lactate_curve_point_invalid_lactate(self) -> None:
        with pytest.raises(ValueError, match="lactate_mmol_l"):
            LactateCurvePoint(stage_number=1, lactate_mmol_l=-0.5)

    def test_lactate_curve_point_invalid_power(self) -> None:
        with pytest.raises(ValueError, match="power_watts"):
            LactateCurvePoint(stage_number=1, lactate_mmol_l=1.5, power_watts=-10.0)

    def test_lactate_curve_point_invalid_speed(self) -> None:
        with pytest.raises(ValueError, match="speed_kph"):
            LactateCurvePoint(stage_number=1, lactate_mmol_l=1.5, speed_kph=-5.0)

    def test_lactate_curve_point_invalid_heart_rate(self) -> None:
        with pytest.raises(ValueError, match="heart_rate_bpm"):
            LactateCurvePoint(stage_number=1, lactate_mmol_l=1.5, heart_rate_bpm=0)

    def test_lactate_curve_empty_test_id(self) -> None:
        with pytest.raises(ValueError, match="test_id"):
            LactateCurve(test_id="", points=())

    def test_lactate_curve_non_tuple_points(self) -> None:
        with pytest.raises(TypeError, match="tuple"):
            LactateCurve(test_id="t1", points=[])  # type: ignore[arg-type]

    def test_lactate_curve_duplicate_stage_numbers(self) -> None:
        p1 = LactateCurvePoint(stage_number=1, lactate_mmol_l=1.0)
        p2 = LactateCurvePoint(stage_number=1, lactate_mmol_l=2.0)
        with pytest.raises(ValueError, match="unique"):
            LactateCurve(test_id="t1", points=(p1, p2))

    def test_lactate_curve_unsorted_stage_numbers(self) -> None:
        p1 = LactateCurvePoint(stage_number=2, lactate_mmol_l=2.0)
        p2 = LactateCurvePoint(stage_number=1, lactate_mmol_l=1.0)
        with pytest.raises(ValueError, match="ascending"):
            LactateCurve(test_id="t1", points=(p1, p2))


# ── Public API & Architecture Boundary Tests ──────────────────────────────────


class TestPublicApiAndBoundaries:
    def test_exports_in_init(self) -> None:
        assert hasattr(performance_lab, "LactateCurvePoint")
        assert hasattr(performance_lab, "LactateCurve")
        assert hasattr(performance_lab, "LactateCurveBuilder")
        assert "LactateCurvePoint" in performance_lab.__all__
        assert "LactateCurve" in performance_lab.__all__
        assert "LactateCurveBuilder" in performance_lab.__all__

    def test_no_forbidden_imports(self) -> None:
        import performance_lab.lactate_curve as lc_module
        import ast

        with open(lc_module.__file__) as f:
            tree = ast.parse(f.read())

        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

        forbidden = {"duckdb", "server", "biomarkers", "recovery", "workout", "decision"}
        overlap = imports & forbidden
        assert not overlap, f"Lactate curve module imports forbidden modules: {overlap}"
