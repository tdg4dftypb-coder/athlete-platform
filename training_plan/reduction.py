"""Shared deterministic load-reduction contract for training-plan consumers."""
from math import isfinite

DURATION_REDUCTION_FACTOR_V1: float = 0.70


def reduced_duration_minutes_v1(source_duration_minutes: int) -> int:
    """Return the canonical v1 reduced duration using established truncation."""
    if not isinstance(source_duration_minutes, int) or isinstance(source_duration_minutes, bool):
        raise TypeError("source_duration_minutes must be int")
    if source_duration_minutes <= 0:
        raise ValueError("source_duration_minutes must be > 0")
    return max(1, int(source_duration_minutes * DURATION_REDUCTION_FACTOR_V1))


def reduced_target_tss_v1(source_target_tss: float | None) -> float | None:
    """Return the canonical v1 proportional target-TSS reduction."""
    if source_target_tss is None:
        return None
    if not isinstance(source_target_tss, (int, float)) or isinstance(source_target_tss, bool):
        raise TypeError("source_target_tss must be numeric when provided")
    if not isfinite(source_target_tss) or source_target_tss < 0:
        raise ValueError("source_target_tss must be finite and >= 0")
    return float(source_target_tss) * DURATION_REDUCTION_FACTOR_V1
