from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnalyzerResult:
    """
    Uniwersalny wynik pojedynczego analizatora.
    """

    status: str
    explanation: str
    recommendation: str


@dataclass
class Alert:

    title: str
    message: str
    severity: str


@dataclass
class MorningBriefing:

    readiness: AnalyzerResult

    energy_balance: Optional[AnalyzerResult] = None

    long_term: Optional[AnalyzerResult] = None

    recommendation: str = ""

    alerts: List[Alert] = field(default_factory=list)