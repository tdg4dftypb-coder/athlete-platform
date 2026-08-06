"""Tests for PerformanceHistoryEntry, PerformanceTestHistory, and PerformanceTestHistoryBuilder — Sprint 21.5."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

import performance_lab
from performance_lab.domain import (
    ExerciseModality,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.history import (
    PerformanceHistoryEntry,
    PerformanceTestHistory,
    PerformanceTestHistoryBuilder,
)
from performance_lab.lactate_curve import (
    LactateCurve,
    LactateCurveBuilder,
    LactateCurvePoint,
)
from performance_lab.thresholds import (
    DetectedThreshold,
    LactateThresholdAnalysis,
    LactateThresholdAnalyzer,
    ThresholdDetectionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

TIME_1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
TIME_2 = datetime(2026, 8, 5, 10, 0, 0, tzinfo=timezone.utc)
TIME_3 = datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc)


def make_session(
    test_id: str,
    performed_at: datetime = TIME_1,
    test_type: PerformanceTestType = PerformanceTestType.LACTATE_STEP_TEST,
    lactate_value: float | None = 2.5,
) -> PerformanceTestSession:
    stage = PerformanceStage(
        stage_number=1,
        completion_status=StageCompletionStatus.COMPLETED,
        lactate_mmol_l=lactate_value,
        power_watts=200.0,
    )
    return PerformanceTestSession(
        test_id=test_id,
        performed_at=performed_at,
        test_type=test_type,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(stage,),
    )


# ── Test Model Invariants ─────────────────────────────────────────────────────


class TestModelInvariants:
    def test_valid_entry(self) -> None:
        session = make_session("t1", test_type=PerformanceTestType.LACTATE_STEP_TEST)
        curve = LactateCurveBuilder().build(session)
        analysis = LactateThresholdAnalyzer().analyze(curve)

        entry = PerformanceHistoryEntry(
            session=session,
            lactate_curve=curve,
            threshold_analysis=analysis,
        )
        assert entry.session == session
        assert entry.lactate_curve == curve
        assert entry.threshold_analysis == analysis

    def test_non_lactate_session_with_curve_rejected(self) -> None:
        session = make_session("t1", test_type=PerformanceTestType.FTP_TEST)
        curve = LactateCurve(test_id="t1", points=())

        with pytest.raises(ValueError, match="lactate_curve must be None"):
            PerformanceHistoryEntry(session=session, lactate_curve=curve)

    def test_non_lactate_session_with_analysis_rejected(self) -> None:
        session = make_session("t1", test_type=PerformanceTestType.FIELD_TEST)
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
        analysis = LactateThresholdAnalysis(test_id="t1", lt1=lt1, lt2=lt2)

        with pytest.raises(ValueError, match="threshold_analysis must be None"):
            PerformanceHistoryEntry(session=session, threshold_analysis=analysis)

    def test_analysis_without_curve_rejected(self) -> None:
        session = make_session("t1", test_type=PerformanceTestType.LACTATE_STEP_TEST)
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
        analysis = LactateThresholdAnalysis(test_id="t1", lt1=lt1, lt2=lt2)

        with pytest.raises(ValueError, match="cannot be present without lactate_curve"):
            PerformanceHistoryEntry(
                session=session,
                lactate_curve=None,
                threshold_analysis=analysis,
            )

    def test_mismatched_curve_test_id_rejected(self) -> None:
        session = make_session("t1")
        curve = LactateCurve(test_id="other_id", points=())

        with pytest.raises(ValueError, match="lactate_curve test_id 'other_id'"):
            PerformanceHistoryEntry(session=session, lactate_curve=curve)

    def test_mismatched_analysis_test_id_rejected(self) -> None:
        session = make_session("t1")
        curve = LactateCurve(test_id="t1", points=())
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
        analysis = LactateThresholdAnalysis(test_id="other_id", lt1=lt1, lt2=lt2)

        with pytest.raises(ValueError, match="threshold_analysis test_id 'other_id'"):
            PerformanceHistoryEntry(
                session=session,
                lactate_curve=curve,
                threshold_analysis=analysis,
            )

    def test_history_non_tuple_rejected(self) -> None:
        with pytest.raises(TypeError, match="tuple"):
            PerformanceTestHistory(entries=[])  # type: ignore[arg-type]

    def test_history_duplicate_test_ids_rejected(self) -> None:
        s1 = make_session("t1", TIME_1)
        s2 = make_session("t1", TIME_2)
        e1 = PerformanceHistoryEntry(session=s1)
        e2 = PerformanceHistoryEntry(session=s2)

        with pytest.raises(ValueError, match="unique"):
            PerformanceTestHistory(entries=(e1, e2))

    def test_history_unsorted_entries_rejected(self) -> None:
        s1 = make_session("t1", TIME_1)
        s2 = make_session("t2", TIME_2)
        e1 = PerformanceHistoryEntry(session=s1)
        e2 = PerformanceHistoryEntry(session=s2)

        with pytest.raises(ValueError, match="chronologically"):
            PerformanceTestHistory(entries=(e2, e1))


# ── Test Builder Logic ────────────────────────────────────────────────────────


class TestPerformanceTestHistoryBuilderLogic:
    def test_empty_input_returns_empty_history(self) -> None:
        builder = PerformanceTestHistoryBuilder()
        history = builder.build(())
        assert history.entries == ()

    def test_single_session_build(self) -> None:
        session = make_session("t1", TIME_1)
        builder = PerformanceTestHistoryBuilder()
        history = builder.build((session,))

        assert len(history.entries) == 1
        entry = history.entries[0]
        assert entry.session.test_id == "t1"
        assert entry.lactate_curve is not None
        assert entry.threshold_analysis is not None

    def test_sorting_oldest_to_newest(self) -> None:
        s1 = make_session("t1", TIME_1)
        s2 = make_session("t2", TIME_2)
        s3 = make_session("t3", TIME_3)

        builder = PerformanceTestHistoryBuilder()
        # Input provided in mixed order
        history = builder.build((s3, s1, s2))

        ids = [e.session.test_id for e in history.entries]
        assert ids == ["t1", "t2", "t3"]

    def test_tie_breaker_by_test_id(self) -> None:
        s_b = make_session("b_test", TIME_1)
        s_a = make_session("a_test", TIME_1)

        builder = PerformanceTestHistoryBuilder()
        history = builder.build((s_b, s_a))

        ids = [e.session.test_id for e in history.entries]
        assert ids == ["a_test", "b_test"]

    def test_deduplication_selects_latest_performed_at(self) -> None:
        s_old = make_session("dup_id", TIME_1)
        s_new = make_session("dup_id", TIME_3)

        builder = PerformanceTestHistoryBuilder()
        history = builder.build((s_old, s_new))

        assert len(history.entries) == 1
        assert history.entries[0].session.performed_at == TIME_3

    def test_deduplication_tie_selects_last_input_occurrence(self) -> None:
        s1 = make_session("dup_id", TIME_1, lactate_value=1.5)
        s2 = make_session("dup_id", TIME_1, lactate_value=3.5)

        builder = PerformanceTestHistoryBuilder()
        history = builder.build((s1, s2))

        assert len(history.entries) == 1
        assert history.entries[0].session.stages[0].lactate_mmol_l == 3.5

    def test_lactate_curve_and_analysis_only_for_lactate_tests(self) -> None:
        s_lactate = make_session("s_lac", TIME_1, PerformanceTestType.LACTATE_STEP_TEST)
        s_ftp = make_session("s_ftp", TIME_2, PerformanceTestType.FTP_TEST)
        s_field = make_session("s_field", TIME_3, PerformanceTestType.FIELD_TEST)

        builder = PerformanceTestHistoryBuilder()
        history = builder.build((s_lactate, s_ftp, s_field))

        e_lac = history.entries[0]
        e_ftp = history.entries[1]
        e_field = history.entries[2]

        assert e_lac.lactate_curve is not None
        assert e_lac.threshold_analysis is not None

        assert e_ftp.lactate_curve is None
        assert e_ftp.threshold_analysis is None

        assert e_field.lactate_curve is None
        assert e_field.threshold_analysis is None

    def test_ftp_test_with_lactate_data_still_bypasses_analysis(self) -> None:
        # Stage accidentally has a lactate value
        s_ftp = make_session("s_ftp", TIME_1, PerformanceTestType.FTP_TEST, lactate_value=4.2)

        builder = PerformanceTestHistoryBuilder()
        history = builder.build((s_ftp,))

        entry = history.entries[0]
        assert entry.lactate_curve is None
        assert entry.threshold_analysis is None

    def test_dependency_injection(self) -> None:
        mock_curve_builder = Mock(spec=LactateCurveBuilder)
        mock_analyzer = Mock(spec=LactateThresholdAnalyzer)

        dummy_curve = LactateCurve(test_id="s1", points=())
        dummy_lt1 = DetectedThreshold("LT1", ThresholdDetectionStatus.NOT_REACHED, 2.0, "fixed_2_mmol")
        dummy_lt2 = DetectedThreshold("LT2", ThresholdDetectionStatus.NOT_REACHED, 4.0, "fixed_4_mmol")
        dummy_analysis = LactateThresholdAnalysis("s1", dummy_lt1, dummy_lt2)

        mock_curve_builder.build.return_value = dummy_curve
        mock_analyzer.analyze.return_value = dummy_analysis

        builder = PerformanceTestHistoryBuilder(
            lactate_curve_builder=mock_curve_builder,
            threshold_analyzer=mock_analyzer,
        )

        s1 = make_session("s1", TIME_1, PerformanceTestType.LACTATE_STEP_TEST)
        s2 = make_session("s2", TIME_2, PerformanceTestType.FTP_TEST)

        history = builder.build((s1, s2))

        # curve builder and analyzer called only for s1
        assert mock_curve_builder.build.call_count == 1
        assert mock_analyzer.analyze.call_count == 1

        mock_curve_builder.build.assert_called_once_with(s1)
        mock_analyzer.analyze.assert_called_once_with(dummy_curve)

        assert history.entries[0].lactate_curve == dummy_curve
        assert history.entries[0].threshold_analysis == dummy_analysis


# ── Public API & Architecture Boundary Tests ──────────────────────────────────


class TestPublicApiAndBoundaries:
    def test_exports_in_init(self) -> None:
        assert hasattr(performance_lab, "PerformanceHistoryEntry")
        assert hasattr(performance_lab, "PerformanceTestHistory")
        assert hasattr(performance_lab, "PerformanceTestHistoryBuilder")

        assert "PerformanceHistoryEntry" in performance_lab.__all__
        assert "PerformanceTestHistory" in performance_lab.__all__
        assert "PerformanceTestHistoryBuilder" in performance_lab.__all__

    def test_no_forbidden_imports(self) -> None:
        import performance_lab.history as hist_module
        import ast

        with open(hist_module.__file__) as f:
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
        assert not overlap, f"History module imports forbidden modules: {overlap}"
