from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DashboardSectionStatus(Enum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class DashboardSection:
    title: str
    status: DashboardSectionStatus
    confidence: float
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class AthleteDashboard:
    decision: DashboardSection | None = None
    body_composition: DashboardSection | None = None
    nutrition: DashboardSection | None = None
    goal: DashboardSection | None = None
    recommendations: DashboardSection | None = None
