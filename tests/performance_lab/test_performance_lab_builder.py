"""Tests for PerformanceTestSessionBuilder — Sprint 21.2."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

import performance_lab
from performance_lab.domain import (
    ExerciseModality,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.input_models import (
    PerformanceStageInput,
    PerformanceTestSessionInput,
)
from performance_lab.builder import PerformanceTestSessionBuilder


# ── Fixtures ──────────────────────────────────────────────────────────────────

NOW = datetime(2026, 8, 6, 9, 0, 0, tzinfo=timezone.utc)


def make_stage_input(
    stage_number: int = 1,
    completion_status: StageCompletionStatus = StageCompletionStatus.COMPLETED,
    **kwargs,
) -> PerformanceStageInput:
    return PerformanceStageInput(
        stage_number=stage_number,
        completion_status=completion_status,
        **kwargs,
    )


def make_session_input(
    stages: tuple[PerformanceStageInput, ...] | None = None,
    status: PerformanceTestStatus = PerformanceTestStatus.COMPLETED,
    **kwargs,
) -> PerformanceTestSessionInput:
    if stages is None:
        stages = (
            make_stage_input(1, power_watts=150.0, lactate_mmol_l=1.2),
            make_stage_input(2, power_watts=200.0, lactate_mmol_l=2.1),
            make_stage_input(3, power_watts=250.0, lactate_mmol_l=4.0),
        )
    return PerformanceTestSessionInput(
        test_id="session-001",
        performed_at=NOW,
        test_type=PerformanceTestType.LACTATE_STEP_TEST,
        status=status,
        modality=ExerciseModality.CYCLING,
        stages=stages,
        **kwargs,
    )


BUILDER = PerformanceTestSessionBuilder()


# ── Builder: full cycling session ─────────────────────────────────────────────


class TestBuilderFullSession:
    def test_full_cycling_session_builds_successfully(self) -> None:
        session = BUILDER.build(make_session_input())
        assert session.test_id == "session-001"
        assert session.modality == ExerciseModality.CYCLING
        assert len(session.stages) == 3

    def test_all_stage_fields_mapped_correctly(self) -> None:
        stage_in = PerformanceStageInput(
            stage_number=4,
            completion_status=StageCompletionStatus.COMPLETED,
            duration_seconds=180,
            power_watts=270.0,
            speed_kph=38.5,
            heart_rate_bpm=168,
            lactate_mmol_l=5.2,
            cadence_rpm=92.0,
            perceived_exertion=8.5,
            notes="Hard effort",
        )
        session_in = make_session_input(stages=(stage_in,))
        session = BUILDER.build(session_in)
        stage = session.stages[0]

        assert stage.stage_number == 4
        assert stage.completion_status == StageCompletionStatus.COMPLETED
        assert stage.duration_seconds == 180
        assert stage.power_watts == 270.0
        assert stage.speed_kph == 38.5
        assert stage.heart_rate_bpm == 168
        assert stage.lactate_mmol_l == 5.2
        assert stage.cadence_rpm == 92.0
        assert stage.perceived_exertion == 8.5
        assert stage.notes == "Hard effort"

    def test_all_session_fields_mapped_correctly(self) -> None:
        session_in = PerformanceTestSessionInput(
            test_id="full-session",
            performed_at=NOW,
            test_type=PerformanceTestType.LACTATE_STEP_TEST,
            status=PerformanceTestStatus.COMPLETED,
            modality=ExerciseModality.CYCLING,
            stages=(make_stage_input(1),),
            protocol_name="3-min step protocol",
            body_mass_kg=72.5,
            ambient_temperature_c=19.0,
            notes="Morning, fasted",
        )
        session = BUILDER.build(session_in)

        assert session.test_id == "full-session"
        assert session.performed_at == NOW
        assert session.test_type == PerformanceTestType.LACTATE_STEP_TEST
        assert session.status == PerformanceTestStatus.COMPLETED
        assert session.modality == ExerciseModality.CYCLING
        assert session.protocol_name == "3-min step protocol"
        assert session.body_mass_kg == 72.5
        assert session.ambient_temperature_c == 19.0
        assert session.notes == "Morning, fasted"


# ── Builder: order and structure ──────────────────────────────────────────────


class TestBuilderOrderAndStructure:
    def test_stage_order_preserved(self) -> None:
        stages = (
            make_stage_input(1, power_watts=150.0),
            make_stage_input(2, power_watts=200.0),
            make_stage_input(3, power_watts=250.0),
        )
        session = BUILDER.build(make_session_input(stages=stages))
        numbers = [s.stage_number for s in session.stages]
        assert numbers == [1, 2, 3]

    def test_stages_are_tuple(self) -> None:
        session = BUILDER.build(make_session_input())
        assert isinstance(session.stages, tuple)

    def test_stage_count_matches_input(self) -> None:
        stages = tuple(make_stage_input(i) for i in range(1, 6))
        session = BUILDER.build(make_session_input(stages=stages))
        assert len(session.stages) == 5


# ── Builder: empty and None handling ─────────────────────────────────────────


class TestBuilderNoneAndEmpty:
    def test_empty_stages_planned_session(self) -> None:
        session_in = make_session_input(
            stages=(),
            status=PerformanceTestStatus.PLANNED,
        )
        session = BUILDER.build(session_in)
        assert session.stages == ()
        assert session.status == PerformanceTestStatus.PLANNED

    def test_none_optional_fields_preserved(self) -> None:
        stage_in = make_stage_input(
            1,
            power_watts=None,
            lactate_mmol_l=None,
            heart_rate_bpm=None,
            notes=None,
        )
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        stage = session.stages[0]
        assert stage.power_watts is None
        assert stage.lactate_mmol_l is None
        assert stage.heart_rate_bpm is None
        assert stage.notes is None

    def test_none_session_optional_fields_preserved(self) -> None:
        session_in = make_session_input(
            protocol_name=None,
            body_mass_kg=None,
            ambient_temperature_c=None,
            notes=None,
        )
        session = BUILDER.build(session_in)
        assert session.protocol_name is None
        assert session.body_mass_kg is None
        assert session.ambient_temperature_c is None
        assert session.notes is None


# ── Builder: completion_status passthrough ─────────────────────────────────────


class TestBuilderCompletionStatus:
    def test_completed_status_preserved(self) -> None:
        stage_in = make_stage_input(1, completion_status=StageCompletionStatus.COMPLETED)
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        assert session.stages[0].completion_status == StageCompletionStatus.COMPLETED

    def test_incomplete_status_preserved(self) -> None:
        stage_in = make_stage_input(1, completion_status=StageCompletionStatus.INCOMPLETE)
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        assert session.stages[0].completion_status == StageCompletionStatus.INCOMPLETE

    def test_skipped_status_preserved(self) -> None:
        stage_in = make_stage_input(1, completion_status=StageCompletionStatus.SKIPPED)
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        assert session.stages[0].completion_status == StageCompletionStatus.SKIPPED


# ── Builder: statelesness and idempotence ────────────────────────────────────


class TestBuilderStatelessness:
    def test_input_not_modified(self) -> None:
        stages = (
            make_stage_input(1, power_watts=150.0),
            make_stage_input(2, power_watts=200.0),
        )
        session_in = make_session_input(stages=stages)
        original_stages = session_in.stages

        BUILDER.build(session_in)

        assert session_in.stages is original_stages
        assert session_in.stages[0].power_watts == 150.0

    def test_two_builds_produce_equal_results(self) -> None:
        session_in = make_session_input()
        result_a = BUILDER.build(session_in)
        result_b = BUILDER.build(session_in)
        assert result_a == result_b

    def test_builder_has_no_internal_state(self) -> None:
        builder_a = PerformanceTestSessionBuilder()
        builder_b = PerformanceTestSessionBuilder()
        session_in = make_session_input()
        assert builder_a.build(session_in) == builder_b.build(session_in)

    def test_different_inputs_produce_different_results(self) -> None:
        in_a = make_session_input(
            stages=(make_stage_input(1, power_watts=150.0),),
        )
        in_b = make_session_input(
            stages=(make_stage_input(1, power_watts=200.0),),
        )
        assert BUILDER.build(in_a) != BUILDER.build(in_b)


# ── Builder: domain validation surfaced ───────────────────────────────────────


class TestBuilderDomainValidation:
    def test_unsorted_stages_rejected(self) -> None:
        stages = (
            make_stage_input(2, power_watts=200.0),
            make_stage_input(1, power_watts=150.0),
        )
        with pytest.raises(ValueError, match="ascending"):
            BUILDER.build(make_session_input(stages=stages))

    def test_duplicate_stage_numbers_rejected(self) -> None:
        stages = (
            make_stage_input(1, power_watts=150.0),
            make_stage_input(1, power_watts=200.0),
        )
        with pytest.raises(ValueError, match="unique"):
            BUILDER.build(make_session_input(stages=stages))

    def test_negative_power_rejected(self) -> None:
        stages = (make_stage_input(1, power_watts=-10.0),)
        with pytest.raises(ValueError, match="power_watts"):
            BUILDER.build(make_session_input(stages=stages))

    def test_heart_rate_zero_rejected(self) -> None:
        stages = (make_stage_input(1, heart_rate_bpm=0),)
        with pytest.raises(ValueError, match="heart_rate_bpm"):
            BUILDER.build(make_session_input(stages=stages))

    def test_empty_test_id_rejected(self) -> None:
        session_in = PerformanceTestSessionInput(
            test_id="",
            performed_at=NOW,
            test_type=PerformanceTestType.LACTATE_STEP_TEST,
            status=PerformanceTestStatus.COMPLETED,
            modality=ExerciseModality.CYCLING,
            stages=(),
        )
        with pytest.raises(ValueError, match="test_id"):
            BUILDER.build(session_in)

    def test_stages_as_list_rejected_at_input_model(self) -> None:
        with pytest.raises(TypeError, match="tuple"):
            PerformanceTestSessionInput(
                test_id="test-001",
                performed_at=NOW,
                test_type=PerformanceTestType.LACTATE_STEP_TEST,
                status=PerformanceTestStatus.COMPLETED,
                modality=ExerciseModality.CYCLING,
                stages=[make_stage_input(1)],  # type: ignore[arg-type]
            )


# ── Builder: no implicit type coercion ───────────────────────────────────────


class TestBuilderNoImplicitCoercion:
    def test_float_value_not_rounded(self) -> None:
        stage_in = make_stage_input(1, lactate_mmol_l=2.3456789)
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        assert session.stages[0].lactate_mmol_l == 2.3456789

    def test_float_power_not_rounded(self) -> None:
        stage_in = make_stage_input(1, power_watts=267.333333)
        session = BUILDER.build(make_session_input(stages=(stage_in,)))
        assert session.stages[0].power_watts == 267.333333

    def test_body_mass_not_rounded(self) -> None:
        session_in = make_session_input(body_mass_kg=72.3456789)
        session = BUILDER.build(session_in)
        assert session.body_mass_kg == 72.3456789

    def test_temperature_not_rounded(self) -> None:
        session_in = make_session_input(ambient_temperature_c=18.666666)
        session = BUILDER.build(session_in)
        assert session.ambient_temperature_c == 18.666666


# ── Public API tests ──────────────────────────────────────────────────────────


class TestPublicApi:
    def test_input_models_exported(self) -> None:
        assert hasattr(performance_lab, "PerformanceStageInput")
        assert hasattr(performance_lab, "PerformanceTestSessionInput")

    def test_builder_exported(self) -> None:
        assert hasattr(performance_lab, "PerformanceTestSessionBuilder")

    def test_all_list_includes_new_exports(self) -> None:
        assert "PerformanceStageInput" in performance_lab.__all__
        assert "PerformanceTestSessionInput" in performance_lab.__all__
        assert "PerformanceTestSessionBuilder" in performance_lab.__all__


# ── Architecture boundary tests ───────────────────────────────────────────────


class TestBuilderArchitectureBoundaries:
    def test_builder_does_not_import_forbidden_modules(self) -> None:
        import performance_lab.builder as builder_module
        source_imports = _get_top_level_imports(builder_module.__file__)
        forbidden = {"duckdb", "server", "biomarkers", "recovery", "workout", "decision"}
        overlap = source_imports & forbidden
        assert not overlap, f"Builder imports forbidden modules: {overlap}"

    def test_input_models_do_not_import_forbidden_modules(self) -> None:
        import performance_lab.input_models as input_module
        source_imports = _get_top_level_imports(input_module.__file__)
        forbidden = {"duckdb", "server", "biomarkers", "recovery", "workout", "decision"}
        overlap = source_imports & forbidden
        assert not overlap, f"Input models import forbidden modules: {overlap}"


def _get_top_level_imports(filepath: str | None) -> set[str]:
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
