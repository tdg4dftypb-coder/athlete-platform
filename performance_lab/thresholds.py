"""Performance Lab — threshold detection models and analyzer.

Sprint 21.4 implementation of fixed-lactate threshold detection (2.0 mmol/L for LT1,
4.0 mmol/L for LT2).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from performance_lab.lactate_curve import LactateCurve, LactateCurvePoint


# ── Enum ──────────────────────────────────────────────────────────────────────


class ThresholdDetectionStatus(Enum):
    DETECTED = "detected"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_REACHED = "not_reached"
    INVALID_CURVE = "invalid_curve"


# ── Models ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DetectedThreshold:
    """Represents the detection outcome for a single threshold (e.g. LT1 or LT2)."""

    name: str
    status: ThresholdDetectionStatus
    target_lactate_mmol_l: float
    method: str

    stage_number: int | None = None
    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    lactate_mmol_l: float | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.target_lactate_mmol_l < 0:
            raise ValueError(
                f"target_lactate_mmol_l must be >= 0, got {self.target_lactate_mmol_l}"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )

        if self.status is ThresholdDetectionStatus.DETECTED:
            if self.stage_number is None:
                raise ValueError("stage_number cannot be None when status is DETECTED")
            if self.lactate_mmol_l is None:
                raise ValueError("lactate_mmol_l cannot be None when status is DETECTED")
        else:
            if self.stage_number is not None:
                raise ValueError(f"stage_number must be None when status is {self.status.name}")
            if self.power_watts is not None:
                raise ValueError(f"power_watts must be None when status is {self.status.name}")
            if self.speed_kph is not None:
                raise ValueError(f"speed_kph must be None when status is {self.status.name}")
            if self.heart_rate_bpm is not None:
                raise ValueError(f"heart_rate_bpm must be None when status is {self.status.name}")
            if self.lactate_mmol_l is not None:
                raise ValueError(f"lactate_mmol_l must be None when status is {self.status.name}")


@dataclass(frozen=True)
class LactateThresholdAnalysis:
    """Aggregate result holding detected LT1 and LT2 thresholds for a test session."""

    test_id: str
    lt1: DetectedThreshold
    lt2: DetectedThreshold

    def __post_init__(self) -> None:
        if not self.test_id:
            raise ValueError("test_id must not be empty")


# ── Analyzer ──────────────────────────────────────────────────────────────────


class LactateThresholdAnalyzer:
    """Fixed-lactate threshold analyzer for LT1 (2.0 mmol/L) and LT2 (4.0 mmol/L).

    Note:
      This fixed 2.0 / 4.0 mmol/L method is a simplified threshold detection method.
      It depends on the test protocol and does not replace professional physiological
      or medical interpretation. Future versions will introduce alternative methods
      (Dmax, modified Dmax, baseline + delta, linear interpolation, etc.).
    """

    def analyze(self, curve: LactateCurve) -> LactateThresholdAnalysis:
        lt1 = self._detect_fixed_threshold(
            curve=curve,
            name="LT1",
            target_lactate=2.0,
            method_name="fixed_2_mmol",
        )
        lt2 = self._detect_fixed_threshold(
            curve=curve,
            name="LT2",
            target_lactate=4.0,
            method_name="fixed_4_mmol",
        )
        return LactateThresholdAnalysis(
            test_id=curve.test_id,
            lt1=lt1,
            lt2=lt2,
        )

    @staticmethod
    def _detect_fixed_threshold(
        curve: LactateCurve,
        name: str,
        target_lactate: float,
        method_name: str,
    ) -> DetectedThreshold:
        if not curve.points:
            return DetectedThreshold(
                name=name,
                status=ThresholdDetectionStatus.INSUFFICIENT_DATA,
                target_lactate_mmol_l=target_lactate,
                method=method_name,
                confidence=None,
            )

        matching_point: LactateCurvePoint | None = None
        for p in curve.points:
            if p.lactate_mmol_l >= target_lactate:
                matching_point = p
                break

        if matching_point is None:
            return DetectedThreshold(
                name=name,
                status=ThresholdDetectionStatus.NOT_REACHED,
                target_lactate_mmol_l=target_lactate,
                method=method_name,
                confidence=None,
            )

        return DetectedThreshold(
            name=name,
            status=ThresholdDetectionStatus.DETECTED,
            target_lactate_mmol_l=target_lactate,
            method=method_name,
            stage_number=matching_point.stage_number,
            power_watts=matching_point.power_watts,
            speed_kph=matching_point.speed_kph,
            heart_rate_bpm=matching_point.heart_rate_bpm,
            lactate_mmol_l=matching_point.lactate_mmol_l,
            confidence=0.6,
        )
