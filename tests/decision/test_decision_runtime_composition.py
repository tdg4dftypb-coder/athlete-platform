from datetime import datetime, timezone
import pytest

from decision import (
    ContextDataStatus,
    DecisionAction,
    DecisionExecutionResult,
    DecisionRuntimeWorkflow,
    create_decision_runtime_workflow,
)
from morning_briefing.input_models import (
    BiomarkerBriefingInput,
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
)
from morning_briefing.provider import MorningBriefingInputError
from performance_lab.builder import PerformanceTestSessionBuilder
from performance_lab.domain import (
    ExerciseModality,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.input_models import PerformanceStageInput, PerformanceTestSessionInput


class CountingMorningBriefingProvider:
    def __init__(self, briefing_input=None):
        self.briefing_input = briefing_input
        self.call_count = 0

    def get_input(self) -> MorningBriefingInput:
        self.call_count += 1
        return self.briefing_input


class CountingPerformanceProvider:
    def __init__(self, sessions=()):
        self.sessions = sessions
        self.call_count = 0

    def get_sessions(self):
        self.call_count += 1
        return self.sessions


def test_create_decision_runtime_workflow_composition():
    gen_at = datetime.now(timezone.utc)
    mb_input = MorningBriefingInput(
        generated_at=gen_at,
        recovery=RecoveryBriefingInput(score=85, status="ready", summary=None, is_stale=False),
        training=TrainingBriefingInput(title="Endurance Ride", description=None, duration_minutes=90, intensity="moderate", is_available=True),
        biomarkers=BiomarkerBriefingInput(available_count=5, attention_count=0, summary=None, is_stale=False),
    )

    mb_provider = CountingMorningBriefingProvider(mb_input)
    perf_provider = CountingPerformanceProvider()

    workflow = create_decision_runtime_workflow(
        morning_briefing_provider=mb_provider,
        performance_test_provider=perf_provider,
    )

    assert isinstance(workflow, DecisionRuntimeWorkflow)
    assert mb_provider.call_count == 0
    assert perf_provider.call_count == 0

    res = workflow.run()

    assert isinstance(res, DecisionExecutionResult)
    assert mb_provider.call_count == 1
    assert perf_provider.call_count == 1

    assert res.record.policy_result.action == DecisionAction.PROCEED
    assert res.record.context.recovery.status == ContextDataStatus.AVAILABLE
    assert res.record.context.training.status == ContextDataStatus.AVAILABLE
    assert res.record.context.biomarkers.status == ContextDataStatus.AVAILABLE
    assert res.record.context.performance.status == ContextDataStatus.UNAVAILABLE


def test_runtime_composition_scenarios():
    gen_at = datetime.now(timezone.utc)

    # 1. Recovery very low -> REST
    mb_rest = MorningBriefingInput(
        generated_at=gen_at,
        recovery=RecoveryBriefingInput(score=20, status="fatigued", summary=None, is_stale=False),
        training=TrainingBriefingInput(title="Intervals", description=None, duration_minutes=60, intensity="high", is_available=True),
        biomarkers=None,
    )
    wf_rest = create_decision_runtime_workflow(
        morning_briefing_provider=CountingMorningBriefingProvider(mb_rest),
        performance_test_provider=CountingPerformanceProvider(),
    )
    res_rest = wf_rest.run()
    assert res_rest.record.policy_result.action == DecisionAction.REST

    # 2. All unavailable -> REVIEW
    wf_unavail = create_decision_runtime_workflow(
        morning_briefing_provider=CountingMorningBriefingProvider(None),
        performance_test_provider=CountingPerformanceProvider(),
    )
    res_unavail = wf_unavail.run()
    assert res_unavail.record.policy_result.action == DecisionAction.REVIEW


def test_architectural_import_isolation():
    import importlib
    import inspect

    mod_wf = importlib.import_module('decision.runtime_workflow')
    source_wf = inspect.getsource(mod_wf)

    prohibited_wf = ['morning_briefing', 'performance_lab', 'recovery', 'training', 'biomarkers', 'server', 'workout', 'duckdb']
    for line in source_wf.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited_wf:
                assert p not in line_clean, f"Prohibited import '{p}' in runtime_workflow.py: {line_clean}"

    mod_comp = importlib.import_module('decision.runtime_composition')
    source_comp = inspect.getsource(mod_comp)

    prohibited_comp = ['server', 'workout', 'duckdb', 'http']
    for line in source_comp.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited_comp:
                assert p not in line_clean, f"Prohibited import '{p}' in runtime_composition.py: {line_clean}"
