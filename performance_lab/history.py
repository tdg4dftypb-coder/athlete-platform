"""Performance Lab — read model for performance test history.

Aggregates PerformanceTestSession objects, optionally computing LactateCurve
and LactateThresholdAnalysis for lactate step tests. Enforces deduplication
and chronological ordering.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from performance_lab.domain import PerformanceTestSession, PerformanceTestType
from performance_lab.lactate_curve import LactateCurve, LactateCurveBuilder
from performance_lab.thresholds import (
    LactateThresholdAnalysis,
    LactateThresholdAnalyzer,
)


# ── Models ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PerformanceHistoryEntry:
    """Read model wrapper for a single performance test session.

    Holds the session and optional lactate analysis artifacts.
    Analysis artifacts are present ONLY for LACTATE_STEP_TEST sessions.
    """

    session: PerformanceTestSession
    lactate_curve: LactateCurve | None = None
    threshold_analysis: LactateThresholdAnalysis | None = None

    def __post_init__(self) -> None:
        if self.session.test_type is not PerformanceTestType.LACTATE_STEP_TEST:
            if self.lactate_curve is not None:
                raise ValueError(
                    f"lactate_curve must be None for test_type {self.session.test_type.name}"
                )
            if self.threshold_analysis is not None:
                raise ValueError(
                    f"threshold_analysis must be None for test_type {self.session.test_type.name}"
                )

        if self.threshold_analysis is not None and self.lactate_curve is None:
            raise ValueError(
                "threshold_analysis cannot be present without lactate_curve"
            )

        if self.lactate_curve is not None:
            if self.lactate_curve.test_id != self.session.test_id:
                raise ValueError(
                    f"lactate_curve test_id '{self.lactate_curve.test_id}' "
                    f"does not match session test_id '{self.session.test_id}'"
                )

        if self.threshold_analysis is not None:
            if self.threshold_analysis.test_id != self.session.test_id:
                raise ValueError(
                    f"threshold_analysis test_id '{self.threshold_analysis.test_id}' "
                    f"does not match session test_id '{self.session.test_id}'"
                )


def _validate_history_entries(entries: tuple[PerformanceHistoryEntry, ...]) -> None:
    """Enforce unique test_ids and chronological ordering."""
    test_ids = [e.session.test_id for e in entries]
    if len(test_ids) != len(set(test_ids)):
        raise ValueError(
            f"PerformanceTestHistory test_id values must be unique, got duplicates: {test_ids}"
        )

    # Check ordering: performed_at ascending, then test_id ascending
    sorted_entries = sorted(
        entries,
        key=lambda e: (e.session.performed_at, e.session.test_id),
    )
    if list(entries) != sorted_entries:
        raise ValueError(
            "PerformanceTestHistory entries must be ordered chronologically by performed_at, "
            "with test_id as tie-breaker"
        )


@dataclass(frozen=True)
class PerformanceTestHistory:
    """Read model aggregating ordered performance test history entries."""

    entries: tuple[PerformanceHistoryEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError(
                f"entries must be a tuple, got {type(self.entries).__name__}"
            )
        _validate_history_entries(self.entries)


# ── Builder ───────────────────────────────────────────────────────────────────


class PerformanceTestHistoryBuilder:
    """Stateless builder: tuple[PerformanceTestSession, ...] -> PerformanceTestHistory.

    - Deduplicates by session.test_id (selecting latest performed_at, or last in input on tie).
    - Sorts entries chronologically by performed_at ascending, with test_id ascending as tie-breaker.
    - Triggers LactateCurveBuilder and LactateThresholdAnalyzer strictly for LACTATE_STEP_TEST.
    """

    def __init__(
        self,
        lactate_curve_builder: LactateCurveBuilder | None = None,
        threshold_analyzer: LactateThresholdAnalyzer | None = None,
    ) -> None:
        self._lactate_curve_builder = lactate_curve_builder or LactateCurveBuilder()
        self._threshold_analyzer = threshold_analyzer or LactateThresholdAnalyzer()

    def build(
        self,
        sessions: Sequence[PerformanceTestSession],
    ) -> PerformanceTestHistory:
        if not sessions:
            return PerformanceTestHistory(entries=())

        deduplicated = self._deduplicate_sessions(sessions)
        sorted_sessions = self._sort_sessions(deduplicated)

        entries = tuple(
            self._create_entry(session) for session in sorted_sessions
        )
        return PerformanceTestHistory(entries=entries)

    # ── Private Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate_sessions(
        sessions: Sequence[PerformanceTestSession],
    ) -> list[PerformanceTestSession]:
        """Deduplicate sessions by test_id.

        Selection rule:
        - Highest performed_at wins.
        - On tie, the session appearing latest in the input sequence wins.
        """
        best_by_id: dict[str, tuple[int, PerformanceTestSession]] = {}
        for index, session in enumerate(sessions):
            tid = session.test_id
            if tid not in best_by_id:
                best_by_id[tid] = (index, session)
            else:
                existing_index, existing_session = best_by_id[tid]
                if session.performed_at > existing_session.performed_at:
                    best_by_id[tid] = (index, session)
                elif session.performed_at == existing_session.performed_at:
                    if index > existing_index:
                        best_by_id[tid] = (index, session)

        return [item[1] for item in best_by_id.values()]

    @staticmethod
    def _sort_sessions(
        sessions: list[PerformanceTestSession],
    ) -> list[PerformanceTestSession]:
        """Sort sessions by performed_at ascending, tie-breaker test_id ascending."""
        return sorted(
            sessions,
            key=lambda s: (s.performed_at, s.test_id),
        )

    def _create_entry(
        self,
        session: PerformanceTestSession,
    ) -> PerformanceHistoryEntry:
        if session.test_type is not PerformanceTestType.LACTATE_STEP_TEST:
            return PerformanceHistoryEntry(
                session=session,
                lactate_curve=None,
                threshold_analysis=None,
            )

        curve = self._lactate_curve_builder.build(session)
        analysis = self._threshold_analyzer.analyze(curve)
        return PerformanceHistoryEntry(
            session=session,
            lactate_curve=curve,
            threshold_analysis=analysis,
        )
