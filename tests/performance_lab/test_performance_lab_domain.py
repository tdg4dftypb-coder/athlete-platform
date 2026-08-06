"""Tests for performance_lab domain models — Sprint 21.1."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from performance_lab.domain import (
    ExerciseModality,
    PerformanceAssessment,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    PerformanceThreshold,
    StageCompletionStatus,
)
import performance_lab  # public package import test


# ── Fixtures ──────────────────────────────────────────────────────────────────

NOW = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)


def make_stage(
    stage_number: int = 1,
    completion_status: StageCompletionStatus = StageCompletionStatus.COMPLETED,
    **kwargs,
) -> PerformanceStage:
    return PerformanceStage(
        stage_number=stage_number,
        completion_status=completion_status,
        **kwargs,
    )


def make_session(
    stages: tuple[PerformanceStage, ...] | None = None,
    status: PerformanceTestStatus = PerformanceTestStatus.COMPLETED,
    **kwargs,
) -> PerformanceTestSession:
    if stages is None:
        stages = (make_stage(1), make_stage(2, power_watts=200.0))
    return PerformanceTestSession(
        test_id="test-001",
        performed_at=NOW,
        test_type=PerformanceTestType.LACTATE_STEP_TEST,
        status=status,
        modality=ExerciseModality.CYCLING,
        stages=stages,
        **kwargs,
    )


def make_threshold(name: str = "LT1", **kwargs) -> PerformanceThreshold:
    return PerformanceThreshold(name=name, **kwargs)


# ── Enum tests ────────────────────────────────────────────────────────────────


class TestPerformanceTestType:
    def test_all_variants_exist(self) -> None:
        assert PerformanceTestType.LACTATE_STEP_TEST
        assert PerformanceTestType.CARDIOPULMONARY_EXERCISE_TEST
        assert PerformanceTestType.FTP_TEST
        assert PerformanceTestType.FIELD_TEST

    def test_stable_values(self) -> None:
        assert PerformanceTestType.LACTATE_STEP_TEST.value == "lactate_step_test"
        assert PerformanceTestType.CARDIOPULMONARY_EXERCISE_TEST.value == "cardiopulmonary_exercise_test"
        assert PerformanceTestType.FTP_TEST.value == "ftp_test"
        assert PerformanceTestType.FIELD_TEST.value == "field_test"

    def test_count(self) -> None:
        assert len(PerformanceTestType) == 4


class TestPerformanceTestStatus:
    def test_all_variants_exist(self) -> None:
        assert PerformanceTestStatus.PLANNED
        assert PerformanceTestStatus.COMPLETED
        assert PerformanceTestStatus.PARTIAL
        assert PerformanceTestStatus.INVALID

    def test_stable_values(self) -> None:
        assert PerformanceTestStatus.PLANNED.value == "planned"
        assert PerformanceTestStatus.COMPLETED.value == "completed"
        assert PerformanceTestStatus.PARTIAL.value == "partial"
        assert PerformanceTestStatus.INVALID.value == "invalid"

    def test_count(self) -> None:
        assert len(PerformanceTestStatus) == 4


class TestExerciseModality:
    def test_all_variants_exist(self) -> None:
        assert ExerciseModality.CYCLING
        assert ExerciseModality.RUNNING
        assert ExerciseModality.ROWING
        assert ExerciseModality.OTHER

    def test_stable_values(self) -> None:
        assert ExerciseModality.CYCLING.value == "cycling"
        assert ExerciseModality.RUNNING.value == "running"
        assert ExerciseModality.ROWING.value == "rowing"
        assert ExerciseModality.OTHER.value == "other"

    def test_count(self) -> None:
        assert len(ExerciseModality) == 4


class TestStageCompletionStatus:
    def test_all_variants_exist(self) -> None:
        assert StageCompletionStatus.COMPLETED
        assert StageCompletionStatus.INCOMPLETE
        assert StageCompletionStatus.SKIPPED

    def test_stable_values(self) -> None:
        assert StageCompletionStatus.COMPLETED.value == "completed"
        assert StageCompletionStatus.INCOMPLETE.value == "incomplete"
        assert StageCompletionStatus.SKIPPED.value == "skipped"

    def test_count(self) -> None:
        assert len(StageCompletionStatus) == 3


# ── PerformanceStage: valid construction ──────────────────────────────────────


class TestPerformanceStageConstruction:
    def test_minimal_stage(self) -> None:
        stage = make_stage(1)
        assert stage.stage_number == 1
        assert stage.completion_status == StageCompletionStatus.COMPLETED
        assert stage.power_watts is None
        assert stage.lactate_mmol_l is None

    def test_fully_populated_stage(self) -> None:
        stage = PerformanceStage(
            stage_number=3,
            completion_status=StageCompletionStatus.COMPLETED,
            duration_seconds=300,
            power_watts=250.0,
            speed_kph=35.0,
            heart_rate_bpm=155,
            lactate_mmol_l=2.5,
            cadence_rpm=90.0,
            perceived_exertion=7.0,
            notes="Steady state achieved",
        )
        assert stage.stage_number == 3
        assert stage.power_watts == 250.0
        assert stage.lactate_mmol_l == 2.5
        assert stage.notes == "Steady state achieved"

    def test_equality(self) -> None:
        a = make_stage(1, power_watts=200.0)
        b = make_stage(1, power_watts=200.0)
        assert a == b

    def test_inequality(self) -> None:
        a = make_stage(1, power_watts=200.0)
        b = make_stage(1, power_watts=210.0)
        assert a != b

    def test_repr_contains_class_name(self) -> None:
        stage = make_stage(1)
        assert "PerformanceStage" in repr(stage)

    def test_frozen_immutable(self) -> None:
        stage = make_stage(1)
        with pytest.raises((AttributeError, TypeError)):
            stage.stage_number = 99  # type: ignore[misc]

    def test_duration_zero_allowed(self) -> None:
        stage = make_stage(1, duration_seconds=0)
        assert stage.duration_seconds == 0

    def test_power_zero_allowed(self) -> None:
        stage = make_stage(1, power_watts=0.0)
        assert stage.power_watts == 0.0

    def test_speed_zero_allowed(self) -> None:
        stage = make_stage(1, speed_kph=0.0)
        assert stage.speed_kph == 0.0

    def test_lactate_zero_allowed(self) -> None:
        stage = make_stage(1, lactate_mmol_l=0.0)
        assert stage.lactate_mmol_l == 0.0

    def test_perceived_exertion_zero_allowed(self) -> None:
        stage = make_stage(1, perceived_exertion=0.0)
        assert stage.perceived_exertion == 0.0

    def test_perceived_exertion_ten_allowed(self) -> None:
        stage = make_stage(1, perceived_exertion=10.0)
        assert stage.perceived_exertion == 10.0

    def test_skipped_stage(self) -> None:
        stage = make_stage(2, completion_status=StageCompletionStatus.SKIPPED)
        assert stage.completion_status == StageCompletionStatus.SKIPPED


# ── PerformanceStage: invariant validation ────────────────────────────────────


class TestPerformanceStageValidation:
    def test_stage_number_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="stage_number"):
            make_stage(0)

    def test_stage_number_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="stage_number"):
            make_stage(-1)

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_seconds"):
            make_stage(1, duration_seconds=-1)

    def test_negative_power_rejected(self) -> None:
        with pytest.raises(ValueError, match="power_watts"):
            make_stage(1, power_watts=-10.0)

    def test_negative_speed_rejected(self) -> None:
        with pytest.raises(ValueError, match="speed_kph"):
            make_stage(1, speed_kph=-5.0)

    def test_heart_rate_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="heart_rate_bpm"):
            make_stage(1, heart_rate_bpm=0)

    def test_heart_rate_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="heart_rate_bpm"):
            make_stage(1, heart_rate_bpm=-1)

    def test_negative_lactate_rejected(self) -> None:
        with pytest.raises(ValueError, match="lactate_mmol_l"):
            make_stage(1, lactate_mmol_l=-0.1)

    def test_negative_cadence_rejected(self) -> None:
        with pytest.raises(ValueError, match="cadence_rpm"):
            make_stage(1, cadence_rpm=-1.0)

    def test_perceived_exertion_below_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="perceived_exertion"):
            make_stage(1, perceived_exertion=-0.1)

    def test_perceived_exertion_above_ten_rejected(self) -> None:
        with pytest.raises(ValueError, match="perceived_exertion"):
            make_stage(1, perceived_exertion=10.1)


# ── PerformanceTestSession: valid construction ────────────────────────────────


class TestPerformanceTestSessionConstruction:
    def test_minimal_session(self) -> None:
        session = make_session()
        assert session.test_id == "test-001"
        assert session.modality == ExerciseModality.CYCLING
        assert len(session.stages) == 2

    def test_empty_stages_allowed_for_planned(self) -> None:
        session = make_session(
            stages=(),
            status=PerformanceTestStatus.PLANNED,
        )
        assert session.stages == ()

    def test_empty_stages_allowed_for_invalid(self) -> None:
        session = make_session(
            stages=(),
            status=PerformanceTestStatus.INVALID,
        )
        assert session.stages == ()

    def test_stages_are_tuple(self) -> None:
        session = make_session()
        assert isinstance(session.stages, tuple)

    def test_fully_populated_session(self) -> None:
        stages = (
            make_stage(1, power_watts=150.0, lactate_mmol_l=1.2),
            make_stage(2, power_watts=200.0, lactate_mmol_l=1.8),
            make_stage(3, power_watts=250.0, lactate_mmol_l=3.5),
        )
        session = PerformanceTestSession(
            test_id="lab-2026-08",
            performed_at=NOW,
            test_type=PerformanceTestType.LACTATE_STEP_TEST,
            status=PerformanceTestStatus.COMPLETED,
            modality=ExerciseModality.CYCLING,
            stages=stages,
            protocol_name="3-min step protocol",
            body_mass_kg=72.5,
            ambient_temperature_c=19.0,
            notes="Morning test, fasted",
        )
        assert session.protocol_name == "3-min step protocol"
        assert session.body_mass_kg == 72.5
        assert len(session.stages) == 3

    def test_equality(self) -> None:
        a = make_session()
        b = make_session()
        assert a == b

    def test_repr_contains_class_name(self) -> None:
        session = make_session()
        assert "PerformanceTestSession" in repr(session)

    def test_frozen_immutable(self) -> None:
        session = make_session()
        with pytest.raises((AttributeError, TypeError)):
            session.test_id = "changed"  # type: ignore[misc]


# ── PerformanceTestSession: invariant validation ──────────────────────────────


class TestPerformanceTestSessionValidation:
    def test_empty_test_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="test_id"):
            PerformanceTestSession(
                test_id="",
                performed_at=NOW,
                test_type=PerformanceTestType.LACTATE_STEP_TEST,
                status=PerformanceTestStatus.COMPLETED,
                modality=ExerciseModality.CYCLING,
                stages=(),
            )

    def test_stages_as_list_rejected(self) -> None:
        with pytest.raises(TypeError, match="tuple"):
            PerformanceTestSession(
                test_id="test-001",
                performed_at=NOW,
                test_type=PerformanceTestType.LACTATE_STEP_TEST,
                status=PerformanceTestStatus.COMPLETED,
                modality=ExerciseModality.CYCLING,
                stages=[make_stage(1)],  # type: ignore[arg-type]
            )

    def test_duplicate_stage_numbers_rejected(self) -> None:
        stages = (make_stage(1), make_stage(1, power_watts=200.0))
        with pytest.raises(ValueError, match="unique"):
            make_session(stages=stages)

    def test_unsorted_stages_rejected(self) -> None:
        stages = (make_stage(2, power_watts=200.0), make_stage(1))
        with pytest.raises(ValueError, match="ascending"):
            make_session(stages=stages)

    def test_body_mass_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="body_mass_kg"):
            make_session(body_mass_kg=0.0)

    def test_body_mass_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="body_mass_kg"):
            make_session(body_mass_kg=-1.0)

    def test_body_mass_positive_accepted(self) -> None:
        session = make_session(body_mass_kg=70.0)
        assert session.body_mass_kg == 70.0


# ── PerformanceThreshold: valid construction ──────────────────────────────────


class TestPerformanceThresholdConstruction:
    def test_minimal_threshold(self) -> None:
        t = make_threshold("LT1")
        assert t.name == "LT1"
        assert t.power_watts is None
        assert t.confidence is None

    def test_fully_populated_threshold(self) -> None:
        t = PerformanceThreshold(
            name="LT2",
            power_watts=280.0,
            speed_kph=42.0,
            heart_rate_bpm=172,
            lactate_mmol_l=4.0,
            confidence=0.92,
            method="Dmax",
        )
        assert t.name == "LT2"
        assert t.confidence == 0.92
        assert t.method == "Dmax"

    def test_confidence_zero_allowed(self) -> None:
        t = make_threshold("LT1", confidence=0.0)
        assert t.confidence == 0.0

    def test_confidence_one_allowed(self) -> None:
        t = make_threshold("LT1", confidence=1.0)
        assert t.confidence == 1.0

    def test_equality(self) -> None:
        a = make_threshold("LT1", power_watts=230.0)
        b = make_threshold("LT1", power_watts=230.0)
        assert a == b

    def test_repr_contains_class_name(self) -> None:
        t = make_threshold()
        assert "PerformanceThreshold" in repr(t)

    def test_frozen_immutable(self) -> None:
        t = make_threshold()
        with pytest.raises((AttributeError, TypeError)):
            t.name = "changed"  # type: ignore[misc]


# ── PerformanceThreshold: invariant validation ────────────────────────────────


class TestPerformanceThresholdValidation:
    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            make_threshold("LT1", confidence=-0.01)

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            make_threshold("LT1", confidence=1.01)

    def test_negative_power_rejected(self) -> None:
        with pytest.raises(ValueError, match="power_watts"):
            make_threshold("LT1", power_watts=-1.0)

    def test_negative_speed_rejected(self) -> None:
        with pytest.raises(ValueError, match="speed_kph"):
            make_threshold("LT1", speed_kph=-1.0)

    def test_heart_rate_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="heart_rate_bpm"):
            make_threshold("LT1", heart_rate_bpm=0)

    def test_negative_lactate_rejected(self) -> None:
        with pytest.raises(ValueError, match="lactate_mmol_l"):
            make_threshold("LT1", lactate_mmol_l=-0.1)


# ── PerformanceAssessment: construction ───────────────────────────────────────


class TestPerformanceAssessmentConstruction:
    def test_minimal_assessment(self) -> None:
        session = make_session()
        assessment = PerformanceAssessment(session=session)
        assert assessment.session is session
        assert assessment.lt1 is None
        assert assessment.lt2 is None
        assert assessment.vo2max_ml_kg_min is None
        assert assessment.fatmax_power_watts is None
        assert assessment.summary is None

    def test_fully_populated_assessment(self) -> None:
        session = make_session()
        lt1 = make_threshold("LT1", power_watts=210.0, confidence=0.88)
        lt2 = make_threshold("LT2", power_watts=275.0, confidence=0.91)
        assessment = PerformanceAssessment(
            session=session,
            lt1=lt1,
            lt2=lt2,
            vo2max_ml_kg_min=62.5,
            fatmax_power_watts=180.0,
            summary="Strong aerobic base. LT1 at 210W, LT2 at 275W.",
        )
        assert assessment.lt1 == lt1
        assert assessment.lt2 == lt2
        assert assessment.vo2max_ml_kg_min == 62.5

    def test_equality(self) -> None:
        session = make_session()
        a = PerformanceAssessment(session=session)
        b = PerformanceAssessment(session=session)
        assert a == b

    def test_repr_contains_class_name(self) -> None:
        assessment = PerformanceAssessment(session=make_session())
        assert "PerformanceAssessment" in repr(assessment)

    def test_frozen_immutable(self) -> None:
        assessment = PerformanceAssessment(session=make_session())
        with pytest.raises((AttributeError, TypeError)):
            assessment.summary = "changed"  # type: ignore[misc]


# ── Architecture boundary tests ───────────────────────────────────────────────


class TestArchitectureBoundaries:
    def test_domain_does_not_import_duckdb(self) -> None:
        import performance_lab.domain as domain_module
        import sys
        # domain.py must not cause DuckDB to be loaded
        assert "duckdb" not in sys.modules or domain_module is not None
        # Directly verify domain module imports only stdlib
        source_imports = _get_top_level_imports(domain_module.__file__)
        forbidden = {"duckdb", "server", "biomarkers", "recovery", "decision", "workout"}
        overlap = source_imports & forbidden
        assert not overlap, f"Domain module imports forbidden modules: {overlap}"

    def test_public_api_exports_all_models(self) -> None:
        assert hasattr(performance_lab, "PerformanceTestType")
        assert hasattr(performance_lab, "PerformanceTestStatus")
        assert hasattr(performance_lab, "ExerciseModality")
        assert hasattr(performance_lab, "StageCompletionStatus")
        assert hasattr(performance_lab, "PerformanceStage")
        assert hasattr(performance_lab, "PerformanceTestSession")
        assert hasattr(performance_lab, "PerformanceThreshold")
        assert hasattr(performance_lab, "PerformanceAssessment")

    def test_public_api_all_list_complete(self) -> None:
        expected = {
            "PerformanceTestType",
            "PerformanceTestStatus",
            "ExerciseModality",
            "StageCompletionStatus",
            "PerformanceStage",
            "PerformanceTestSession",
            "PerformanceThreshold",
            "PerformanceAssessment",
        }
        assert expected.issubset(set(performance_lab.__all__))


def _get_top_level_imports(filepath: str | None) -> set[str]:
    """Parse top-level import names from a Python source file."""
    if filepath is None:
        return set()
    import ast
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports
