from datetime import datetime

from decision.context import ContextDataStatus, RecoveryDecisionContext
from morning_briefing.input_models import MorningBriefingInput, RecoveryBriefingInput
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


class DefaultRecoveryDecisionContextAdapter:
    """Adapter converting Recovery input from MorningBriefingInputProvider or MorningBriefingInput to RecoveryDecisionContext."""

    def __init__(self, provider: MorningBriefingInputProvider) -> None:
        if provider is None:
            raise TypeError("provider must not be None")
        self._provider = provider

    def get_context(
        self,
        generated_at: datetime,
        briefing_input: MorningBriefingInput | None = None,
    ) -> RecoveryDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        if briefing_input is None:
            try:
                briefing_input = self._provider.get_input()
            except MorningBriefingInputError:
                return RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        if briefing_input is None or briefing_input.recovery is None:
            return RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        rec: RecoveryBriefingInput = briefing_input.recovery

        # Check STALE
        if rec.is_stale:
            status = ContextDataStatus.STALE
        elif rec.score is None or rec.status is None:
            status = ContextDataStatus.PARTIAL
        else:
            status = ContextDataStatus.AVAILABLE

        score_val = float(rec.score) if rec.score is not None else None

        return RecoveryDecisionContext(
            status=status,
            recovery_score=score_val,
            recovery_status=rec.status,
            hrv_status=rec.hrv_status,
            resting_heart_rate_status=rec.resting_heart_rate_status,
            sleep_status=rec.sleep_status,
            generated_at=briefing_input.generated_at,
        )
