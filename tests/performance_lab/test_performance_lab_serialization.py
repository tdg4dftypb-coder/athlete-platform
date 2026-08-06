"""Tests for PerformanceTestHistorySerializer — Sprint 21.6A."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
import pytest

from performance_lab.domain import (
    ExerciseModality,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.history import PerformanceTestHistoryBuilder
from performance_lab.serialization import PerformanceTestHistorySerializer

TIME_1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
TIME_2 = datetime(2026, 8, 5, 12, 30, 0, tzinfo=timezone.utc)

SERIALIZER = PerformanceTestHistorySerializer()
BUILDER = PerformanceTestHistoryBuilder()


def make_lactate_session(test_id: str = "lac-001") -> PerformanceTestSession:
    stage1 = PerformanceStage(
        stage_number=1,
        completion_status=StageCompletionStatus.COMPLETED,
        duration_seconds=180,
        power_watts=120.0,
        speed_kph=None,
        heart_rate_bpm=110,
        lactate_mmol_l=1.1,
        cadence_rpm=85.0,
        perceived_exertion=2.0,
        notes=None,
    )
    stage2 = PerformanceStage(
        stage_number=2,
        completion_status=StageCompletionStatus.COMPLETED,
        duration_seconds=180,
        power_watts=160.0,
        speed_kph=None,
        heart_rate_bpm=130,
        lactate_mmol_l=2.2,
        cadence_rpm=88.0,
        perceived_exertion=4.0,
        notes=None,
    )
    stage3 = PerformanceStage(
        stage_number=3,
        completion_status=StageCompletionStatus.COMPLETED,
        duration_seconds=180,
        power_watts=200.0,
        speed_kph=None,
        heart_rate_bpm=150,
        lactate_mmol_l=4.2,
        cadence_rpm=90.0,
        perceived_exertion=7.0,
        notes=None,
    )
    return PerformanceTestSession(
        test_id=test_id,
        performed_at=TIME_1,
        test_type=PerformanceTestType.LACTATE_STEP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(stage1, stage2, stage3),
        protocol_name="Ramp 40W/3min",
        body_mass_kg=75.0,
        ambient_temperature_c=21.5,
        notes="Fasted morning test",
    )


def make_ftp_session(test_id: str = "ftp-001") -> PerformanceTestSession:
    stage = PerformanceStage(
        stage_number=1,
        completion_status=StageCompletionStatus.COMPLETED,
        duration_seconds=1200,
        power_watts=280.0,
        speed_kph=None,
        heart_rate_bpm=172,
        lactate_mmol_l=None,
        cadence_rpm=95.0,
        perceived_exertion=9.0,
        notes="20min max effort",
    )
    return PerformanceTestSession(
        test_id=test_id,
        performed_at=TIME_2,
        test_type=PerformanceTestType.FTP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(stage,),
        protocol_name="20-min FTP",
        body_mass_kg=75.0,
        ambient_temperature_c=22.0,
        notes="Fresh legs",
    )


def assert_recursive_json_primitives(val: Any) -> None:
    """Helper verifying val consists exclusively of JSON primitive types."""
    if val is None or isinstance(val, (bool, int, float, str)):
        return
    if isinstance(val, list):
        for item in val:
            assert_recursive_json_primitives(item)
        return
    if isinstance(val, dict):
        for k, v in val.items():
            assert isinstance(k, str), f"Dict key {k!r} is not a str"
            assert_recursive_json_primitives(v)
        return
    pytest.fail(f"Value {val!r} of type {type(val)} is not a valid JSON primitive")


class TestPerformanceTestHistorySerializer:
    def test_empty_history_serialization(self) -> None:
        history = BUILDER.build(())
        payload = SERIALIZER.serialize(history)
        assert payload == {"entries": []}
        assert set(payload.keys()) == {"entries"}
        assert json.loads(json.dumps(payload)) == payload

    def test_exact_key_sets_for_all_levels(self) -> None:
        history = BUILDER.build((make_lactate_session(),))
        payload = SERIALIZER.serialize(history)

        # 2. Main level
        assert set(payload.keys()) == {"entries"}

        # 3. Entry level
        entry = payload["entries"][0]
        assert set(entry.keys()) == {"session", "lactate_curve", "threshold_analysis"}

        # 4. Session level
        session = entry["session"]
        expected_session_keys = {
            "test_id",
            "performed_at",
            "test_type",
            "status",
            "modality",
            "protocol_name",
            "body_mass_kg",
            "ambient_temperature_c",
            "notes",
            "stages",
        }
        assert set(session.keys()) == expected_session_keys

        # 5. Stage level
        stage = session["stages"][0]
        expected_stage_keys = {
            "stage_number",
            "duration_seconds",
            "power_watts",
            "speed_kph",
            "heart_rate_bpm",
            "lactate_mmol_l",
            "cadence_rpm",
            "perceived_exertion",
            "completion_status",
            "notes",
        }
        assert set(stage.keys()) == expected_stage_keys

        # 6. Lactate curve level
        curve = entry["lactate_curve"]
        assert set(curve.keys()) == {"test_id", "points"}

        # 7. Curve point level
        point = curve["points"][0]
        expected_point_keys = {
            "stage_number",
            "power_watts",
            "speed_kph",
            "heart_rate_bpm",
            "lactate_mmol_l",
            "absolute_change_mmol_l",
            "relative_change_percent",
        }
        assert set(point.keys()) == expected_point_keys

        # 8. Threshold analysis level
        analysis = entry["threshold_analysis"]
        assert set(analysis.keys()) == {"test_id", "lt1", "lt2"}

        # 9. DetectedThreshold level
        expected_threshold_keys = {
            "name",
            "status",
            "stage_number",
            "power_watts",
            "speed_kph",
            "heart_rate_bpm",
            "lactate_mmol_l",
            "target_lactate_mmol_l",
            "confidence",
            "method",
        }
        assert set(analysis["lt1"].keys()) == expected_threshold_keys
        assert set(analysis["lt2"].keys()) == expected_threshold_keys

    def test_full_lactate_session_serialization_values(self) -> None:
        history = BUILDER.build((make_lactate_session(),))
        payload = SERIALIZER.serialize(history)

        entry = payload["entries"][0]
        session = entry["session"]
        assert session["test_id"] == "lac-001"
        assert session["performed_at"] == TIME_1.isoformat()
        assert session["test_type"] == "lactate_step_test"
        assert session["status"] == "completed"
        assert session["modality"] == "cycling"
        assert session["protocol_name"] == "Ramp 40W/3min"

        curve = entry["lactate_curve"]
        assert curve["test_id"] == "lac-001"
        assert len(curve["points"]) == 3

        lt1 = entry["threshold_analysis"]["lt1"]
        assert lt1["status"] == "detected"
        assert lt1["stage_number"] == 2
        assert lt1["power_watts"] == 160.0

    def test_non_lactate_session_null_curve_and_analysis(self) -> None:
        history = BUILDER.build((make_ftp_session(),))
        payload = SERIALIZER.serialize(history)

        entry = payload["entries"][0]
        assert entry["session"]["test_type"] == "ftp_test"
        assert entry["lactate_curve"] is None
        assert entry["threshold_analysis"] is None

    def test_ordering_and_structure_preserved(self) -> None:
        s1 = make_lactate_session("s1")  # TIME_1
        s2 = make_ftp_session("s2")      # TIME_2
        history = BUILDER.build((s2, s1))
        original_history_entries = history.entries

        payload = SERIALIZER.serialize(history)

        # Input history unmodified
        assert history.entries is original_history_entries

        # Ordering preserved
        ids = [e["session"]["test_id"] for e in payload["entries"]]
        assert ids == ["s1", "s2"]

        stages_numbers = [st["stage_number"] for st in payload["entries"][0]["session"]["stages"]]
        assert stages_numbers == [1, 2, 3]

        points_numbers = [pt["stage_number"] for pt in payload["entries"][0]["lactate_curve"]["points"]]
        assert points_numbers == [1, 2, 3]

    def test_recursive_json_primitives_safety(self) -> None:
        history = BUILDER.build((make_lactate_session(), make_ftp_session()))
        payload = SERIALIZER.serialize(history)

        # Recursive check ensuring only primitives
        assert_recursive_json_primitives(payload)
