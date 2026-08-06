"""Performance Lab — JSON serialization for test history.

Provides JSON-safe dictionary serialization of PerformanceTestHistory,
PerformanceHistoryEntry, LactateCurve, and LactateThresholdAnalysis.
"""
from __future__ import annotations

from typing import Any

from performance_lab.domain import PerformanceStage, PerformanceTestSession
from performance_lab.history import PerformanceHistoryEntry, PerformanceTestHistory
from performance_lab.lactate_curve import LactateCurve, LactateCurvePoint
from performance_lab.thresholds import DetectedThreshold, LactateThresholdAnalysis


class PerformanceTestHistorySerializer:
    """Stateless serializer converting PerformanceTestHistory into JSON-safe dicts."""

    def serialize(self, history: PerformanceTestHistory) -> dict[str, Any]:
        """Serialize PerformanceTestHistory into a JSON-safe dictionary."""
        return {
            "entries": [
                self._serialize_entry(entry) for entry in history.entries
            ]
        }

    # ── Private Serialization Helpers ─────────────────────────────────────────

    def _serialize_entry(self, entry: PerformanceHistoryEntry) -> dict[str, Any]:
        return {
            "session": self._serialize_session(entry.session),
            "lactate_curve": (
                self._serialize_lactate_curve(entry.lactate_curve)
                if entry.lactate_curve is not None
                else None
            ),
            "threshold_analysis": (
                self._serialize_threshold_analysis(entry.threshold_analysis)
                if entry.threshold_analysis is not None
                else None
            ),
        }

    def _serialize_session(self, session: PerformanceTestSession) -> dict[str, Any]:
        return {
            "test_id": session.test_id,
            "performed_at": session.performed_at.isoformat(),
            "test_type": session.test_type.value,
            "status": session.status.value,
            "modality": session.modality.value,
            "protocol_name": session.protocol_name,
            "body_mass_kg": session.body_mass_kg,
            "ambient_temperature_c": session.ambient_temperature_c,
            "notes": session.notes,
            "stages": [self._serialize_stage(stage) for stage in session.stages],
        }

    @staticmethod
    def _serialize_stage(stage: PerformanceStage) -> dict[str, Any]:
        return {
            "stage_number": stage.stage_number,
            "duration_seconds": stage.duration_seconds,
            "power_watts": stage.power_watts,
            "speed_kph": stage.speed_kph,
            "heart_rate_bpm": stage.heart_rate_bpm,
            "lactate_mmol_l": stage.lactate_mmol_l,
            "cadence_rpm": stage.cadence_rpm,
            "perceived_exertion": stage.perceived_exertion,
            "completion_status": stage.completion_status.value,
            "notes": stage.notes,
        }

    def _serialize_lactate_curve(self, curve: LactateCurve) -> dict[str, Any]:
        return {
            "test_id": curve.test_id,
            "points": [self._serialize_curve_point(p) for p in curve.points],
        }

    @staticmethod
    def _serialize_curve_point(point: LactateCurvePoint) -> dict[str, Any]:
        return {
            "stage_number": point.stage_number,
            "power_watts": point.power_watts,
            "speed_kph": point.speed_kph,
            "heart_rate_bpm": point.heart_rate_bpm,
            "lactate_mmol_l": point.lactate_mmol_l,
            "absolute_change_mmol_l": point.absolute_change_mmol_l,
            "relative_change_percent": point.relative_change_percent,
        }

    def _serialize_threshold_analysis(
        self, analysis: LactateThresholdAnalysis
    ) -> dict[str, Any]:
        return {
            "test_id": analysis.test_id,
            "lt1": self._serialize_detected_threshold(analysis.lt1),
            "lt2": self._serialize_detected_threshold(analysis.lt2),
        }

    @staticmethod
    def _serialize_detected_threshold(threshold: DetectedThreshold) -> dict[str, Any]:
        return {
            "name": threshold.name,
            "status": threshold.status.value,
            "stage_number": threshold.stage_number,
            "power_watts": threshold.power_watts,
            "speed_kph": threshold.speed_kph,
            "heart_rate_bpm": threshold.heart_rate_bpm,
            "lactate_mmol_l": threshold.lactate_mmol_l,
            "target_lactate_mmol_l": threshold.target_lactate_mmol_l,
            "confidence": threshold.confidence,
            "method": threshold.method,
        }
