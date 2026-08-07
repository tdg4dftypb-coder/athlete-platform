"""Application adapter converting TrainingPlan and MorningBriefingInput into TrainingDecisionContext."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from decision.context import ContextDataStatus, TrainingDecisionContext
from decision.context_adapters.protocols import TrainingDecisionContextAdapter
from morning_briefing.input_models import MorningBriefingInput, TrainingBriefingInput
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider
from training_plan.models import PlannedSessionKind
from training_plan.ports import TrainingPlanProvider
from training_plan.repository import TrainingPlanRepositoryError


class MissingTrainingPlanError(Exception):
    """Raised when no baseline TrainingPlan is available for the requested run date."""


class TrainingPlanDecisionContextAdapter(TrainingDecisionContextAdapter):
    """Production application adapter providing TrainingDecisionContext from a persisted TrainingPlan."""

    def __init__(
        self,
        training_plan_provider: TrainingPlanProvider,
        briefing_provider: MorningBriefingInputProvider | None = None,
        default_timezone_name: str = "Europe/Warsaw",
    ) -> None:
        if training_plan_provider is None:
            raise TypeError("training_plan_provider must not be None")
        self._plan_provider = training_plan_provider
        self._briefing_provider = briefing_provider
        self._tz_name = default_timezone_name

    def get_context(
        self,
        generated_at: datetime,
        briefing_input: MorningBriefingInput | None = None,
    ) -> TrainingDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        # Resolve local date in configured timezone
        if generated_at.tzinfo is not None:
            local_dt = generated_at.astimezone(ZoneInfo(self._tz_name))
        else:
            local_dt = generated_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(self._tz_name))

        target_date: date = local_dt.date()

        # Query plan provider ONCE for exact plan snapshot
        try:
            plan = self._plan_provider.get_plan_for_date(target_date)
        except TrainingPlanRepositoryError as e:
            raise RuntimeError(f"Training Plan source failure: {e}") from e

        if plan is None:
            raise MissingTrainingPlanError(f"No baseline TrainingPlan found covering target date {target_date}")

        # Retrieve exact session slot for target date from the loaded plan snapshot
        session_slot = None
        for s in plan.sessions:
            if s.date == target_date:
                session_slot = s
                break

        if session_slot is None:
            raise MissingTrainingPlanError(f"No session slot in plan '{plan.plan_id}' for target date {target_date}")

        # Optionally load MorningBriefingInput for recent_training_load and fatigue_status
        # Morning Briefing enrichment (optional recent_load & fatigue_status)
        if briefing_input is None and self._briefing_provider is not None:
            try:
                briefing_input = self._briefing_provider.get_input()
            except (MorningBriefingInputError, Exception):
                briefing_input = None

        recent_load = None
        fatigue_status = None
        if briefing_input and briefing_input.training:
            recent_load = briefing_input.training.recent_training_load
            fatigue_status = briefing_input.training.fatigue_status

        # Map according to session kind (TRAINING vs REST)
        if session_slot.kind == PlannedSessionKind.TRAINING:
            return TrainingDecisionContext(
                status=ContextDataStatus.AVAILABLE,
                planned_session_type=session_slot.session_type,
                planned_duration_minutes=session_slot.duration_minutes,
                planned_intensity=session_slot.intensity,
                recent_training_load=recent_load,
                fatigue_status=fatigue_status,
                generated_at=generated_at,
                plan_id=plan.plan_id,
                planned_session_id=session_slot.session_id,
            )
        else:
            # Explicit REST mapping
            return TrainingDecisionContext(
                status=ContextDataStatus.AVAILABLE,
                planned_session_type="REST",
                planned_duration_minutes=0,
                planned_intensity=None,
                recent_training_load=recent_load,
                fatigue_status=fatigue_status,
                generated_at=generated_at,
                plan_id=plan.plan_id,
                planned_session_id=session_slot.session_id,
            )
