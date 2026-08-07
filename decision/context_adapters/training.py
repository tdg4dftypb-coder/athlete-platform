from datetime import datetime

from decision.context import ContextDataStatus, TrainingDecisionContext
from morning_briefing.input_models import MorningBriefingInput, TrainingBriefingInput
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


class DefaultTrainingDecisionContextAdapter:
    """Adapter converting Training input from MorningBriefingInputProvider or MorningBriefingInput to TrainingDecisionContext."""

    def __init__(self, provider: MorningBriefingInputProvider) -> None:
        if provider is None:
            raise TypeError("provider must not be None")
        self._provider = provider

    def get_context(
        self,
        generated_at: datetime,
        briefing_input: MorningBriefingInput | None = None,
    ) -> TrainingDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        if briefing_input is None:
            try:
                briefing_input = self._provider.get_input()
            except MorningBriefingInputError:
                return TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        if briefing_input is None or briefing_input.training is None:
            return TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        tr: TrainingBriefingInput = briefing_input.training

        if not tr.is_available:
            return TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)

        # Planned session type mapping
        session_type = tr.title.lower() if tr.title else None

        return TrainingDecisionContext(
            status=ContextDataStatus.AVAILABLE,
            planned_session_type=session_type,
            planned_duration_minutes=tr.duration_minutes,
            planned_intensity=tr.intensity,
            recent_training_load=None,
            fatigue_status=None,
            generated_at=briefing_input.generated_at,
        )
