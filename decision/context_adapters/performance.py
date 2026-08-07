from datetime import datetime

from decision.context import (
    ContextDataStatus,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
)
from performance_lab.history import PerformanceHistoryEntry, PerformanceTestHistoryBuilder
from performance_lab.provider import PerformanceTestSessionProvider, PerformanceTestSessionProviderError


class DefaultPerformanceDecisionContextAdapter:
    """Adapter converting Performance Lab history into PerformanceDecisionContext."""

    def __init__(
        self,
        provider: PerformanceTestSessionProvider,
        history_builder: PerformanceTestHistoryBuilder | None = None,
    ) -> None:
        if provider is None:
            raise TypeError("provider must not be None")
        self._provider = provider
        self._history_builder = history_builder or PerformanceTestHistoryBuilder()

    def get_context(self, generated_at: datetime) -> PerformanceDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        try:
            sessions = self._provider.get_sessions()
        except PerformanceTestSessionProviderError:
            return PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        if not sessions:
            return PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        history = self._history_builder.build(sessions)
        if not history.entries:
            return PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        # Select latest entry (history is ordered oldest -> newest)
        latest_entry: PerformanceHistoryEntry = history.entries[-1]
        session = latest_entry.session
        thresh_analysis = latest_entry.threshold_analysis

        lt1_snapshot = None
        lt2_snapshot = None

        if thresh_analysis and thresh_analysis.lt1:
            lt1 = thresh_analysis.lt1
            lt1_snapshot = PerformanceThresholdSnapshot(
                name="LT1",
                status=lt1.status.name.lower(),
                power_watts=lt1.power_watts,
                speed_kph=lt1.speed_kph,
                heart_rate_bpm=lt1.heart_rate_bpm,
                lactate_mmol_l=lt1.lactate_mmol_l,
                confidence=lt1.confidence,
                method=str(lt1.method),
            )

        if thresh_analysis and thresh_analysis.lt2:
            lt2 = thresh_analysis.lt2
            lt2_snapshot = PerformanceThresholdSnapshot(
                name="LT2",
                status=lt2.status.name.lower(),
                power_watts=lt2.power_watts,
                speed_kph=lt2.speed_kph,
                heart_rate_bpm=lt2.heart_rate_bpm,
                lactate_mmol_l=lt2.lactate_mmol_l,
                confidence=lt2.confidence,
                method=str(lt2.method),
            )

        return PerformanceDecisionContext(
            status=ContextDataStatus.AVAILABLE,
            latest_test_id=session.test_id,
            latest_test_type=session.test_type.name.lower(),
            performed_at=session.performed_at,
            lt1=lt1_snapshot,
            lt2=lt2_snapshot,
        )
