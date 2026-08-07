from datetime import datetime, timezone
import pytest

from decision import (
    ContextDataStatus,
    DecisionAction,
    DecisionExecutionRequest,
    DecisionExecutionService,
    DefaultBiomarkerDecisionContextAdapter,
    DefaultPerformanceDecisionContextAdapter,
    DefaultRecoveryDecisionContextAdapter,
    DefaultTrainingDecisionContextAdapter,
    RuntimeAthleteDecisionContextProvider,
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
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.input_models import PerformanceStageInput, PerformanceTestSessionInput



from performance_lab.provider import PerformanceTestSessionProviderError


class StubMorningBriefingProvider:
    def __init__(self, briefing_input=None, raise_error=False):
        self.briefing_input = briefing_input
        self.raise_error = raise_error
        self.call_count = 0

    def get_input(self) -> MorningBriefingInput:
        self.call_count += 1
        if self.raise_error:
            raise MorningBriefingInputError("Morning briefing unavailable")
        return self.briefing_input


class StubPerformanceProvider:
    def __init__(self, sessions=(), raise_error=False):
        self.sessions = sessions
        self.raise_error = raise_error
        self.call_count = 0

    def get_sessions(self) -> tuple[PerformanceTestSession, ...]:
        self.call_count += 1
        if self.raise_error:
            raise PerformanceTestSessionProviderError("Performance source unavailable")
        return self.sessions


def test_recovery_adapter():
    gen_at = datetime.now(timezone.utc)
    rec_input = RecoveryBriefingInput(score=85, status="ready", summary="Good recovery", is_stale=False)
    briefing = MorningBriefingInput(generated_at=gen_at, recovery=rec_input, training=None, biomarkers=None)

    provider = StubMorningBriefingProvider(briefing)
    adapter = DefaultRecoveryDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert provider.call_count == 1
    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.recovery_score == 85.0
    assert ctx.recovery_status == "ready"
    assert ctx.generated_at == gen_at

    # Partial score
    rec_partial = RecoveryBriefingInput(score=None, status="ready", summary=None, is_stale=False)
    adapter_p = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, rec_partial, None, None)))
    assert adapter_p.get_context(gen_at).status == ContextDataStatus.PARTIAL

    # Stale score
    rec_stale = RecoveryBriefingInput(score=80, status="ready", summary=None, is_stale=True)
    adapter_s = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, rec_stale, None, None)))
    assert adapter_s.get_context(gen_at).status == ContextDataStatus.STALE

    # Provider error
    adapter_err = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(raise_error=True))
    assert adapter_err.get_context(gen_at).status == ContextDataStatus.UNAVAILABLE


def test_training_adapter():
    gen_at = datetime.now(timezone.utc)
    tr_input = TrainingBriefingInput(title="Endurance Ride", description="Zone 2", duration_minutes=90, intensity="moderate", is_available=True)
    briefing = MorningBriefingInput(generated_at=gen_at, recovery=None, training=tr_input, biomarkers=None)

    provider = StubMorningBriefingProvider(briefing)
    adapter = DefaultTrainingDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.planned_session_type == "endurance ride"
    assert ctx.planned_duration_minutes == 90
    assert ctx.planned_intensity == "moderate"

    # Plan missing but source available
    tr_none = TrainingBriefingInput(title=None, description=None, duration_minutes=None, intensity=None, is_available=True)
    adapter_none = DefaultTrainingDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, None, tr_none, None)))
    ctx_none = adapter_none.get_context(gen_at)
    assert ctx_none.status == ContextDataStatus.AVAILABLE
    assert ctx_none.planned_session_type is None


def test_biomarkers_adapter():
    gen_at = datetime.now(timezone.utc)
    bio_input = BiomarkerBriefingInput(available_count=10, attention_count=2, summary="Ferritin low", is_stale=False)
    briefing = MorningBriefingInput(generated_at=gen_at, recovery=None, training=None, biomarkers=bio_input)

    provider = StubMorningBriefingProvider(briefing)
    adapter = DefaultBiomarkerDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.attention_count == 2
    assert len(ctx.signals) == 1
    assert ctx.signals[0].canonical_code == "LAB_SUMMARY"

    # Zero attention -> AVAILABLE with empty signals
    bio_clean = BiomarkerBriefingInput(available_count=10, attention_count=0, summary=None, is_stale=False)
    adapter_clean = DefaultBiomarkerDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, None, None, bio_clean)))
    ctx_clean = adapter_clean.get_context(gen_at)
    assert ctx_clean.status == ContextDataStatus.AVAILABLE
    assert len(ctx_clean.signals) == 0


def test_performance_adapter():
    gen_at = datetime.now(timezone.utc)

    stage1 = PerformanceStageInput(stage_number=1, completion_status=StageCompletionStatus.COMPLETED, power_watts=150.0, lactate_mmol_l=1.8, heart_rate_bpm=120)
    stage2 = PerformanceStageInput(stage_number=2, completion_status=StageCompletionStatus.COMPLETED, power_watts=200.0, lactate_mmol_l=2.2, heart_rate_bpm=140)
    stage3 = PerformanceStageInput(stage_number=3, completion_status=StageCompletionStatus.COMPLETED, power_watts=250.0, lactate_mmol_l=4.5, heart_rate_bpm=165)

    sess_input = PerformanceTestSessionInput(
        test_id="perf-01",
        performed_at=gen_at,
        test_type=PerformanceTestType.LACTATE_STEP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(stage1, stage2, stage3),
    )

    session = PerformanceTestSessionBuilder().build(sess_input)



    provider = StubPerformanceProvider(sessions=(session,))
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.latest_test_id == "perf-01"
    assert ctx.lt1 is not None
    assert ctx.lt2 is not None

    # Empty provider
    adapter_empty = DefaultPerformanceDecisionContextAdapter(StubPerformanceProvider(sessions=()))
    assert adapter_empty.get_context(gen_at).status == ContextDataStatus.UNAVAILABLE


def test_runtime_context_provider_order_and_execution():
    gen_at = datetime.now(timezone.utc)
    mb_provider = StubMorningBriefingProvider(
        MorningBriefingInput(
            generated_at=gen_at,
            recovery=RecoveryBriefingInput(score=85, status="ready", summary=None, is_stale=False),
            training=TrainingBriefingInput(title="Intervals", description=None, duration_minutes=60, intensity="high", is_available=True),
            biomarkers=BiomarkerBriefingInput(available_count=5, attention_count=0, summary=None, is_stale=False),
        )
    )

    rec_adapter = DefaultRecoveryDecisionContextAdapter(mb_provider)
    tr_adapter = DefaultTrainingDecisionContextAdapter(mb_provider)
    bio_adapter = DefaultBiomarkerDecisionContextAdapter(mb_provider)
    perf_adapter = DefaultPerformanceDecisionContextAdapter(StubPerformanceProvider())

    runtime_provider = RuntimeAthleteDecisionContextProvider(
        recovery_adapter=rec_adapter,
        training_adapter=tr_adapter,
        biomarker_adapter=bio_adapter,
        performance_adapter=perf_adapter,
        briefing_provider=mb_provider,
    )

    ctx = runtime_provider.build_context(gen_at)

    assert mb_provider.call_count == 1
    assert ctx.generated_at == gen_at
    assert ctx.recovery.status == ContextDataStatus.AVAILABLE
    assert ctx.training.status == ContextDataStatus.AVAILABLE
    assert ctx.biomarkers.status == ContextDataStatus.AVAILABLE
    assert ctx.performance.status == ContextDataStatus.UNAVAILABLE


def test_unexpected_errors_are_propagated():
    class BrokenProvider:
        def get_input(self):
            raise TypeError("Unexpected type error in provider")

    adapter = DefaultRecoveryDecisionContextAdapter(BrokenProvider())  # type: ignore
    with pytest.raises(TypeError, match="Unexpected type error"):
        adapter.get_context(datetime.now(timezone.utc))


def test_architectural_import_isolation():
    import importlib
    import inspect

    modules_checks = [
        ('decision.context_adapters.recovery', ['training', 'biomarkers', 'performance_lab', 'workout', 'server']),
        ('decision.context_adapters.training', ['recovery', 'biomarkers', 'performance_lab', 'workout', 'server']),
        ('decision.context_adapters.biomarkers', ['recovery', 'training', 'performance_lab', 'server']),
        ('decision.context_adapters.performance', ['recovery', 'training', 'biomarkers', 'server']),
        ('decision.context_adapters.runtime_provider', ['recovery', 'training', 'biomarkers', 'performance_lab', 'server', 'workout']),

    ]

    for mod_name, prohibited in modules_checks:
        mod = importlib.import_module(mod_name)
        source = inspect.getsource(mod)
        for line in source.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("import ") or line_clean.startswith("from "):
                for p in prohibited:
                    assert p not in line_clean, f"Prohibited import '{p}' found in {mod_name}: {line_clean}"



def test_integration_with_execution_service():
    gen_at = datetime.now(timezone.utc)
    mb_provider = StubMorningBriefingProvider(
        MorningBriefingInput(
            generated_at=gen_at,
            recovery=RecoveryBriefingInput(score=85, status="ready", summary=None, is_stale=False),
            training=TrainingBriefingInput(title="Endurance Ride", description=None, duration_minutes=90, intensity="moderate", is_available=True),
            biomarkers=BiomarkerBriefingInput(available_count=5, attention_count=0, summary=None, is_stale=False),
        )
    )

    runtime_provider = RuntimeAthleteDecisionContextProvider(
        recovery_adapter=DefaultRecoveryDecisionContextAdapter(mb_provider),
        training_adapter=DefaultTrainingDecisionContextAdapter(mb_provider),
        biomarker_adapter=DefaultBiomarkerDecisionContextAdapter(mb_provider),
        performance_adapter=DefaultPerformanceDecisionContextAdapter(StubPerformanceProvider()),
    )

    service = DecisionExecutionService(context_provider=runtime_provider)
    req = DecisionExecutionRequest(decision_id="integ-01", generated_at=gen_at, recorded_at=gen_at)

    result = service.execute(req)

    assert result.record.decision_id == "integ-01"
    assert result.record.policy_result.action == DecisionAction.PROCEED
    assert result.record.recommendation_plan.recommendations[0].code == "proceed_as_planned"
