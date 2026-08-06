"""Tests for LactateThresholdAnalyzer, DetectedThreshold, and LactateThresholdAnalysis — Sprint 21.4."""
from __future__ import annotations

import pytest

import performance_lab
from performance_lab.lactate_curve import LactateCurve, LactateCurvePoint
from performance_lab.thresholds import (
    DetectedThreshold,
    LactateThresholdAnalysis,
    LactateThresholdAnalyzer,
    ThresholdDetectionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

ANALYZER = LactateThresholdAnalyzer()


def make_curve(points: tuple[LactateCurvePoint, ...] = (), test_id: str = "test-001") -> LactateCurve:
    return LactateCurve(test_id=test_id, points=points)


def make_point(
    stage_number: int,
    lactate: float,
    power: float | None = None,
    speed: float | None = None,
    hr: int | None = None,
) -> LactateCurvePoint:
    return LactateCurvePoint(
        stage_number=stage_number,
        lactate_mmol_l=lactate,
        power_watts=power,
        speed_kph=speed,
        heart_rate_bpm=hr,
    )


# ── Test LT1 / LT2 Detection Logic ───────────────────────────────────────────


class TestLactateThresholdAnalyzerLogic:
    def test_exact_and_above_threshold_detection(self) -> None:
        p1 = make_point(1, 1.2, power=150.0, hr=130)
        p2 = make_point(2, 2.0, power=200.0, hr=145)  # exact 2.0 for LT1
        p3 = make_point(3, 4.5, power=250.0, hr=165)  # above 4.0 for LT2
        curve = make_curve((p1, p2, p3))

        analysis = ANALYZER.analyze(curve)

        assert analysis.test_id == "test-001"

        # LT1
        lt1 = analysis.lt1
        assert lt1.name == "LT1"
        assert lt1.status == ThresholdDetectionStatus.DETECTED
        assert lt1.target_lactate_mmol_l == 2.0
        assert lt1.method == "fixed_2_mmol"
        assert lt1.confidence == 0.6
        assert lt1.stage_number == 2
        assert lt1.power_watts == 200.0
        assert lt1.lactate_mmol_l == 2.0
        assert lt1.heart_rate_bpm == 145

        # LT2
        lt2 = analysis.lt2
        assert lt2.name == "LT2"
        assert lt2.status == ThresholdDetectionStatus.DETECTED
        assert lt2.target_lactate_mmol_l == 4.0
        assert lt2.method == "fixed_4_mmol"
        assert lt2.confidence == 0.6
        assert lt2.stage_number == 3
        assert lt2.power_watts == 250.0
        assert lt2.lactate_mmol_l == 4.5
        assert lt2.heart_rate_bpm == 165

    def test_picks_first_qualifying_point(self) -> None:
        p1 = make_point(1, 2.5, power=180.0)  # qualifies for LT1
        p2 = make_point(2, 3.2, power=220.0)  # also > 2.0, but second
        p3 = make_point(3, 4.0, power=260.0)  # qualifies for LT2
        p4 = make_point(4, 5.5, power=300.0)  # also > 4.0, but second
        curve = make_curve((p1, p2, p3, p4))

        analysis = ANALYZER.analyze(curve)
        assert analysis.lt1.stage_number == 1
        assert analysis.lt1.lactate_mmol_l == 2.5
        assert analysis.lt2.stage_number == 3
        assert analysis.lt2.lactate_mmol_l == 4.0

    def test_empty_curve_returns_insufficient_data(self) -> None:
        curve = make_curve(())
        analysis = ANALYZER.analyze(curve)

        assert analysis.lt1.status == ThresholdDetectionStatus.INSUFFICIENT_DATA
        assert analysis.lt1.target_lactate_mmol_l == 2.0
        assert analysis.lt1.method == "fixed_2_mmol"
        assert analysis.lt1.confidence is None
        assert analysis.lt1.stage_number is None

        assert analysis.lt2.status == ThresholdDetectionStatus.INSUFFICIENT_DATA
        assert analysis.lt2.target_lactate_mmol_l == 4.0
        assert analysis.lt2.method == "fixed_4_mmol"
        assert analysis.lt2.confidence is None
        assert analysis.lt2.stage_number is None

    def test_points_below_targets_returns_not_reached(self) -> None:
        p1 = make_point(1, 1.2, power=150.0)
        p2 = make_point(2, 1.8, power=180.0)
        curve = make_curve((p1, p2))

        analysis = ANALYZER.analyze(curve)

        assert analysis.lt1.status == ThresholdDetectionStatus.NOT_REACHED
        assert analysis.lt1.target_lactate_mmol_l == 2.0
        assert analysis.lt1.confidence is None
        assert analysis.lt1.stage_number is None

        assert analysis.lt2.status == ThresholdDetectionStatus.NOT_REACHED
        assert analysis.lt2.target_lactate_mmol_l == 4.0
        assert analysis.lt2.confidence is None
        assert analysis.lt2.stage_number is None

    def test_lt1_detected_lt2_not_reached(self) -> None:
        p1 = make_point(1, 1.2, power=150.0)
        p2 = make_point(2, 2.3, power=200.0)
        p3 = make_point(3, 3.5, power=240.0)
        curve = make_curve((p1, p2, p3))

        analysis = ANALYZER.analyze(curve)

        assert analysis.lt1.status == ThresholdDetectionStatus.DETECTED
        assert analysis.lt1.stage_number == 2
        assert analysis.lt2.status == ThresholdDetectionStatus.NOT_REACHED
        assert analysis.lt2.stage_number is None

    def test_missing_optional_metrics_in_qualifying_point_allowed(self) -> None:
        p1 = make_point(1, 2.2, power=None, speed=None, hr=None)
        curve = make_curve((p1,))

        analysis = ANALYZER.analyze(curve)

        assert analysis.lt1.status == ThresholdDetectionStatus.DETECTED
        assert analysis.lt1.stage_number == 1
        assert analysis.lt1.lactate_mmol_l == 2.2
        assert analysis.lt1.power_watts is None
        assert analysis.lt1.speed_kph is None
        assert analysis.lt1.heart_rate_bpm is None

    def test_lactate_drop_supported_without_exception(self) -> None:
        p1 = make_point(1, 2.2, power=150.0)
        p2 = make_point(2, 1.8, power=180.0)  # drop
        p3 = make_point(3, 4.2, power=250.0)
        curve = make_curve((p1, p2, p3))

        analysis = ANALYZER.analyze(curve)
        assert analysis.lt1.status == ThresholdDetectionStatus.DETECTED
        assert analysis.lt1.stage_number == 1
        assert analysis.lt2.status == ThresholdDetectionStatus.DETECTED
        assert analysis.lt2.stage_number == 3

    def test_statelessness_and_idempotence(self) -> None:
        p1 = make_point(1, 2.1)
        p2 = make_point(2, 4.1)
        curve = make_curve((p1, p2))

        res1 = ANALYZER.analyze(curve)
        res2 = ANALYZER.analyze(curve)

        assert res1 == res2


# ── Test Model Invariants ─────────────────────────────────────────────────────


class TestDetectedThresholdInvariants:
    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name"):
            DetectedThreshold(
                name="",
                status=ThresholdDetectionStatus.NOT_REACHED,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
            )

    def test_negative_target_lactate_rejected(self) -> None:
        with pytest.raises(ValueError, match="target_lactate_mmol_l"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.NOT_REACHED,
                target_lactate_mmol_l=-1.0,
                method="fixed_2_mmol",
            )

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.NOT_REACHED,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
                confidence=1.5,
            )

    def test_detected_without_stage_number_rejected(self) -> None:
        with pytest.raises(ValueError, match="stage_number"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.DETECTED,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
                stage_number=None,
                lactate_mmol_l=2.1,
            )

    def test_detected_without_lactate_rejected(self) -> None:
        with pytest.raises(ValueError, match="lactate_mmol_l"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.DETECTED,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
                stage_number=1,
                lactate_mmol_l=None,
            )

    def test_not_detected_with_point_fields_rejected(self) -> None:
        with pytest.raises(ValueError, match="stage_number"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.NOT_REACHED,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
                stage_number=1,
            )

        with pytest.raises(ValueError, match="lactate_mmol_l"):
            DetectedThreshold(
                name="LT1",
                status=ThresholdDetectionStatus.INSUFFICIENT_DATA,
                target_lactate_mmol_l=2.0,
                method="fixed_2_mmol",
                lactate_mmol_l=1.8,
            )

    def test_analysis_empty_test_id_rejected(self) -> None:
        lt1 = DetectedThreshold(
            name="LT1",
            status=ThresholdDetectionStatus.NOT_REACHED,
            target_lactate_mmol_l=2.0,
            method="fixed_2_mmol",
        )
        lt2 = DetectedThreshold(
            name="LT2",
            status=ThresholdDetectionStatus.NOT_REACHED,
            target_lactate_mmol_l=4.0,
            method="fixed_4_mmol",
        )
        with pytest.raises(ValueError, match="test_id"):
            LactateThresholdAnalysis(test_id="", lt1=lt1, lt2=lt2)


# ── Public API & Architecture Boundary Tests ──────────────────────────────────


class TestPublicApiAndBoundaries:
    def test_exports_in_init(self) -> None:
        assert hasattr(performance_lab, "ThresholdDetectionStatus")
        assert hasattr(performance_lab, "DetectedThreshold")
        assert hasattr(performance_lab, "LactateThresholdAnalysis")
        assert hasattr(performance_lab, "LactateThresholdAnalyzer")

        assert "ThresholdDetectionStatus" in performance_lab.__all__
        assert "DetectedThreshold" in performance_lab.__all__
        assert "LactateThresholdAnalysis" in performance_lab.__all__
        assert "LactateThresholdAnalyzer" in performance_lab.__all__

    def test_no_forbidden_imports(self) -> None:
        import performance_lab.thresholds as thresh_module
        import ast

        with open(thresh_module.__file__) as f:
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
        assert not overlap, f"Thresholds module imports forbidden modules: {overlap}"
