from datetime import datetime

from decision.context import AthleteDecisionContext
from decision.context_builder import AthleteDecisionContextBuilder
from decision.context_adapters.protocols import (
    BiomarkerDecisionContextAdapter,
    PerformanceDecisionContextAdapter,
    RecoveryDecisionContextAdapter,
    TrainingDecisionContextAdapter,
)
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


class RuntimeAthleteDecisionContextProvider:
    """Concrete provider implementing AthleteDecisionContextProvider protocol.

    Aggregates neutral domain context adapters and uses AthleteDecisionContextBuilder
    to compose the unified AthleteDecisionContext. Ensures MorningBriefingInput is fetched
    exactly ONCE per build_context() invocation.
    """

    def __init__(
        self,
        recovery_adapter: RecoveryDecisionContextAdapter,
        training_adapter: TrainingDecisionContextAdapter,
        biomarker_adapter: BiomarkerDecisionContextAdapter,
        performance_adapter: PerformanceDecisionContextAdapter,
        briefing_provider: MorningBriefingInputProvider | None = None,
        builder: AthleteDecisionContextBuilder | None = None,
    ) -> None:
        if recovery_adapter is None:
            raise TypeError("recovery_adapter must not be None")
        if training_adapter is None:
            raise TypeError("training_adapter must not be None")
        if biomarker_adapter is None:
            raise TypeError("biomarker_adapter must not be None")
        if performance_adapter is None:
            raise TypeError("performance_adapter must not be None")

        self._recovery_adapter = recovery_adapter
        self._training_adapter = training_adapter
        self._biomarker_adapter = biomarker_adapter
        self._performance_adapter = performance_adapter
        self._briefing_provider = briefing_provider
        self._builder = builder or AthleteDecisionContextBuilder()

    def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        # Single request-scoped snapshot for Morning Briefing sources
        briefing_snapshot = None
        if self._briefing_provider is not None:
            try:
                briefing_snapshot = self._briefing_provider.get_input()
            except MorningBriefingInputError:
                briefing_snapshot = None

        # Order of execution: Recovery -> Training -> Biomarkers -> Performance
        if hasattr(self._recovery_adapter, "get_context") and "briefing_input" in self._recovery_adapter.get_context.__code__.co_varnames:
            recovery = self._recovery_adapter.get_context(generated_at, briefing_input=briefing_snapshot)
        else:
            recovery = self._recovery_adapter.get_context(generated_at)

        if hasattr(self._training_adapter, "get_context") and "briefing_input" in self._training_adapter.get_context.__code__.co_varnames:
            training = self._training_adapter.get_context(generated_at, briefing_input=briefing_snapshot)
        else:
            training = self._training_adapter.get_context(generated_at)

        if hasattr(self._biomarker_adapter, "get_context") and "briefing_input" in self._biomarker_adapter.get_context.__code__.co_varnames:
            biomarkers = self._biomarker_adapter.get_context(generated_at, briefing_input=briefing_snapshot)
        else:
            biomarkers = self._biomarker_adapter.get_context(generated_at)

        performance = self._performance_adapter.get_context(generated_at)

        return self._builder.build(
            generated_at=generated_at,
            recovery=recovery,
            training=training,
            biomarkers=biomarkers,
            performance=performance,
        )
