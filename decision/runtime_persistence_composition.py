from dataclasses import dataclass

from decision.audit_provider import DecisionAuditRecordProvider
from decision.persisted_runtime import PersistedDecisionRuntimeWorkflow
from decision.repository import DecisionAuditRecordRepository
from decision.repository_audit_provider import RepositoryDecisionAuditRecordProvider
from decision.runtime_composition import create_decision_runtime_workflow
from decision.runtime_workflow import DecisionClock, DecisionIdGenerator
from morning_briefing.provider import MorningBriefingInputProvider
from performance_lab.provider import PerformanceTestSessionProvider


@dataclass(frozen=True)
class DecisionRuntimeApplication:
    """Encapsulates configured Decision Intelligence runtime workflow, latest provider, and repository."""

    workflow: PersistedDecisionRuntimeWorkflow
    latest_provider: DecisionAuditRecordProvider
    repository: DecisionAuditRecordRepository


def create_persisted_decision_runtime_application(
    morning_briefing_provider: MorningBriefingInputProvider,
    performance_test_provider: PerformanceTestSessionProvider,
    repository: DecisionAuditRecordRepository,
    *,
    clock: DecisionClock | None = None,
    id_generator: DecisionIdGenerator | None = None,
) -> DecisionRuntimeApplication:
    """Factory composing the persisted Decision Intelligence 2.0 application runtime."""
    if morning_briefing_provider is None:
        raise TypeError("morning_briefing_provider must not be None")
    if performance_test_provider is None:
        raise TypeError("performance_test_provider must not be None")
    if repository is None:
        raise TypeError("repository must not be None")

    inner_workflow = create_decision_runtime_workflow(
        morning_briefing_provider=morning_briefing_provider,
        performance_test_provider=performance_test_provider,
        clock=clock,
        id_generator=id_generator,
    )

    persisted_workflow = PersistedDecisionRuntimeWorkflow(
        runtime_workflow=inner_workflow,
        repository=repository,
    )

    latest_provider = RepositoryDecisionAuditRecordProvider(repository=repository)

    return DecisionRuntimeApplication(
        workflow=persisted_workflow,
        latest_provider=latest_provider,
        repository=repository,
    )
