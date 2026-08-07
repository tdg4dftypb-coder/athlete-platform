from decision.context_adapters import (
    DefaultBiomarkerDecisionContextAdapter,
    DefaultPerformanceDecisionContextAdapter,
    DefaultRecoveryDecisionContextAdapter,
    DefaultTrainingDecisionContextAdapter,
    RuntimeAthleteDecisionContextProvider,
)
from decision.execution_service import DecisionExecutionService
from decision.runtime_workflow import (
    DecisionClock,
    DecisionIdGenerator,
    DecisionRuntimeWorkflow,
    SystemUtcDecisionClock,
    UuidDecisionIdGenerator,
)
from morning_briefing.provider import MorningBriefingInputProvider
from performance_lab.provider import PerformanceTestHistoryProvider


def create_decision_runtime_workflow(
    morning_briefing_provider: MorningBriefingInputProvider,
    performance_history_provider: PerformanceTestHistoryProvider,
    *,
    clock: DecisionClock | None = None,
    id_generator: DecisionIdGenerator | None = None,
    training_adapter: Any | None = None,
) -> DecisionRuntimeWorkflow:
    """Factory composing the production/runtime Decision Intelligence 2.0 workflow graph.

    Single MorningBriefingInputProvider snapshot is shared across Recovery, Training, and Biomarkers
    during RuntimeAthleteDecisionContextProvider.build_context() execution.
    """
    if morning_briefing_provider is None:
        raise TypeError("morning_briefing_provider must not be None")
    if performance_history_provider is None:
        raise TypeError("performance_history_provider must not be None")

    rec_adapter = DefaultRecoveryDecisionContextAdapter(morning_briefing_provider)
    tr_adapter = training_adapter or DefaultTrainingDecisionContextAdapter(morning_briefing_provider)
    bio_adapter = DefaultBiomarkerDecisionContextAdapter(morning_briefing_provider)
    perf_adapter = DefaultPerformanceDecisionContextAdapter(performance_history_provider)

    context_provider = RuntimeAthleteDecisionContextProvider(
        recovery_adapter=rec_adapter,
        training_adapter=tr_adapter,
        biomarker_adapter=bio_adapter,
        performance_adapter=perf_adapter,
        briefing_provider=morning_briefing_provider,
    )

    execution_service = DecisionExecutionService(context_provider=context_provider)

    effective_clock = clock or SystemUtcDecisionClock()
    effective_id_generator = id_generator or UuidDecisionIdGenerator()

    return DecisionRuntimeWorkflow(
        execution_service=execution_service,
        clock=effective_clock,
        id_generator=effective_id_generator,
    )
