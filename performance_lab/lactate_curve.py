"""Performance Lab — lactate curve models and builder.

Builds a LactateCurve from a PerformanceTestSession by selecting
completed stages with a valid lactate value and computing point-to-point
changes. No threshold detection, no interpolation, no analysis.
"""
from __future__ import annotations

from dataclasses import dataclass

from performance_lab.domain import (
    PerformanceTestSession,
    PerformanceStage,
    StageCompletionStatus,
)


# ── Models ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LactateCurvePoint:
    """One qualified data point on the lactate curve.

    Only stages with completion_status == COMPLETED and a non-None
    lactate_mmol_l value appear here. Change fields are None for the
    first point and for the relative change when the previous lactate
    value is zero.
    """

    stage_number: int
    lactate_mmol_l: float

    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    absolute_change_mmol_l: float | None = None
    relative_change_percent: float | None = None

    def __post_init__(self) -> None:
        if self.stage_number < 1:
            raise ValueError(
                f"stage_number must be >= 1, got {self.stage_number}"
            )
        if self.lactate_mmol_l < 0:
            raise ValueError(
                f"lactate_mmol_l must be >= 0, got {self.lactate_mmol_l}"
            )
        if self.power_watts is not None and self.power_watts < 0:
            raise ValueError(
                f"power_watts must be >= 0, got {self.power_watts}"
            )
        if self.speed_kph is not None and self.speed_kph < 0:
            raise ValueError(
                f"speed_kph must be >= 0, got {self.speed_kph}"
            )
        if self.heart_rate_bpm is not None and self.heart_rate_bpm <= 0:
            raise ValueError(
                f"heart_rate_bpm must be > 0, got {self.heart_rate_bpm}"
            )


def _validate_curve_points(points: tuple[LactateCurvePoint, ...]) -> None:
    """Enforce unique, ascending stage_numbers across all curve points."""
    numbers = [p.stage_number for p in points]
    if len(numbers) != len(set(numbers)):
        raise ValueError(
            f"LactateCurve stage_number values must be unique, got: {numbers}"
        )
    if numbers != sorted(numbers):
        raise ValueError(
            f"LactateCurve points must be ordered by ascending stage_number, "
            f"got: {numbers}"
        )


@dataclass(frozen=True)
class LactateCurve:
    """Ordered sequence of lactate data points derived from a test session."""

    test_id: str
    points: tuple[LactateCurvePoint, ...]

    def __post_init__(self) -> None:
        if not self.test_id:
            raise ValueError("test_id must not be empty")
        if not isinstance(self.points, tuple):
            raise TypeError(
                f"points must be a tuple, got {type(self.points).__name__}"
            )
        _validate_curve_points(self.points)


# ── Builder ───────────────────────────────────────────────────────────────────


class LactateCurveBuilder:
    """Stateless builder: PerformanceTestSession → LactateCurve.

    Qualification rules:
      1. completion_status == StageCompletionStatus.COMPLETED
      2. lactate_mmol_l is not None

    Stages that are INCOMPLETE, SKIPPED, or lack a lactate value are
    silently omitted — they are not errors.

    Change computation:
      - First point: absolute_change = None, relative_change = None
      - Subsequent points:
          absolute = current_lactate - previous_lactate
          relative = (absolute / previous_lactate) * 100
                     or None when previous_lactate == 0
    """

    def build(self, session: PerformanceTestSession) -> LactateCurve:
        qualified = self._qualify_stages(session)
        points = self._compute_points(qualified)
        return LactateCurve(test_id=session.test_id, points=points)

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _qualify_stages(session: PerformanceTestSession) -> list[PerformanceStage]:
        return [
            stage
            for stage in session.stages
            if (
                stage.completion_status is StageCompletionStatus.COMPLETED
                and stage.lactate_mmol_l is not None
            )
        ]

    @staticmethod
    def _compute_points(
        stages: list[PerformanceStage],
    ) -> tuple[LactateCurvePoint, ...]:
        points: list[LactateCurvePoint] = []
        prev_lactate: float | None = None

        for stage in stages:
            lactate: float = stage.lactate_mmol_l  # type: ignore[assignment]
            # guaranteed non-None by _qualify_stages

            absolute_change: float | None = None
            relative_change: float | None = None

            if prev_lactate is not None:
                absolute_change = lactate - prev_lactate
                if prev_lactate != 0.0:
                    relative_change = (absolute_change / prev_lactate) * 100.0
                # when prev_lactate == 0: relative_change stays None

            points.append(
                LactateCurvePoint(
                    stage_number=stage.stage_number,
                    lactate_mmol_l=lactate,
                    power_watts=stage.power_watts,
                    speed_kph=stage.speed_kph,
                    heart_rate_bpm=stage.heart_rate_bpm,
                    absolute_change_mmol_l=absolute_change,
                    relative_change_percent=relative_change,
                )
            )
            prev_lactate = lactate

        return tuple(points)
