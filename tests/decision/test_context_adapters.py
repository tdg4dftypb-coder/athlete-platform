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
    rec_input = RecoveryBriefingInput(
        score=85,
        status="ready",
        summary="Good recovery",
        is_stale=False,
        hrv_status="supportive",
        resting_heart_rate_status="neutral",
        sleep_status="caution",
    )
    briefing = MorningBriefingInput(generated_at=gen_at, recovery=rec_input, training=None, biomarkers=None)

    provider = StubMorningBriefingProvider(briefing)
    adapter = DefaultRecoveryDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert provider.call_count == 1
    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.recovery_score == 85.0
    assert ctx.recovery_status == "ready"
    assert ctx.hrv_status == "supportive"
    assert ctx.resting_heart_rate_status == "neutral"
    assert ctx.sleep_status == "caution"
    assert ctx.generated_at == gen_at

    # Partial score with metric statuses
    rec_partial = RecoveryBriefingInput(
        score=None,
        status="ready",
        summary=None,
        is_stale=False,
        hrv_status=None,
        resting_heart_rate_status=None,
        sleep_status=None,
    )
    adapter_p = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, rec_partial, None, None)))
    ctx_p = adapter_p.get_context(gen_at)
    assert ctx_p.status == ContextDataStatus.PARTIAL
    assert ctx_p.hrv_status is None

    # Stale score
    rec_stale = RecoveryBriefingInput(score=80, status="ready", summary=None, is_stale=True)
    adapter_s = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(MorningBriefingInput(gen_at, rec_stale, None, None)))
    assert adapter_s.get_context(gen_at).status == ContextDataStatus.STALE

    # Provider error
    adapter_err = DefaultRecoveryDecisionContextAdapter(StubMorningBriefingProvider(raise_error=True))
    assert adapter_err.get_context(gen_at).status == ContextDataStatus.UNAVAILABLE


def test_training_adapter():
    gen_at = datetime.now(timezone.utc)
    tr_input = TrainingBriefingInput(
        title="Sweet Spot Builder",
        description="Zone 2",
        duration_minutes=90,
        intensity="moderate",
        is_available=True,
        session_type="tempo",  # Canonical session_type from DecisionResult
        recent_training_load=450.0,
        fatigue_status="high",
    )
    briefing = MorningBriefingInput(generated_at=gen_at, recovery=None, training=tr_input, biomarkers=None)

    provider = StubMorningBriefingProvider(briefing)
    adapter = DefaultTrainingDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.planned_session_type == "tempo"  # Canonical value preferred over title.lower() "sweet spot builder"
    assert ctx.planned_duration_minutes == 90
    assert ctx.planned_intensity == "moderate"
    assert ctx.recent_training_load == 450.0
    assert ctx.fatigue_status == "high"

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


from performance_lab.provider import (
    EmptyPerformanceTestHistoryProvider,
    PerformanceTestHistoryProviderError,
)
from performance_lab.history import (
    PerformanceHistoryEntry,
    PerformanceTestHistory,
    PerformanceTestHistoryBuilder,
)


class StubPerformanceHistoryProvider:
    def __init__(self, history=None, raise_error=False):
        self.history = history or PerformanceTestHistory(entries=())
        self.raise_error = raise_error
        self.call_count = 0

    def get_history(self) -> PerformanceTestHistory:
        self.call_count += 1
        if self.raise_error:
            raise PerformanceTestHistoryProviderError("Performance history source unavailable")
        return self.history


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
    # Pre-analyzed history built outside Decision Intelligence
    history = PerformanceTestHistoryBuilder().build((session,))

    provider = StubPerformanceHistoryProvider(history=history)
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.latest_test_id == "perf-01"
    assert ctx.lt1 is not None
    assert ctx.lt2 is not None


def test_performance_adapter_empty_history():
    provider = StubPerformanceHistoryProvider(history=PerformanceTestHistory(entries=()))
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(datetime.now(timezone.utc))
    assert ctx.status == ContextDataStatus.UNAVAILABLE


def test_performance_adapter_provider_error():
    provider = StubPerformanceHistoryProvider(raise_error=True)
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(datetime.now(timezone.utc))
    assert ctx.status == ContextDataStatus.UNAVAILABLE


def test_performance_adapter_non_lactate_test_without_thresholds():
    gen_at = datetime.now(timezone.utc)
    session = PerformanceTestSession(
        test_id="ftp-01",
        performed_at=gen_at,
        test_type=PerformanceTestType.FTP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(),
    )
    # History entry without threshold analysis (non-lactate test)
    entry = PerformanceHistoryEntry(session=session, threshold_analysis=None)
    history = PerformanceTestHistory(entries=(entry,))

    provider = StubPerformanceHistoryProvider(history=history)
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(gen_at)

    assert ctx.status == ContextDataStatus.AVAILABLE
    assert ctx.latest_test_id == "ftp-01"
    assert ctx.latest_test_type == "ftp_test"
    assert ctx.performed_at == gen_at
    assert ctx.lt1 is None
    assert ctx.lt2 is None


def test_performance_adapter_selects_latest_entry_without_reordering():
    gen_at1 = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    gen_at2 = datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)
    sess1 = PerformanceTestSession(
        test_id="old-01",
        performed_at=gen_at1,
        test_type=PerformanceTestType.FTP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(),
    )
    sess2 = PerformanceTestSession(
        test_id="new-02",
        performed_at=gen_at2,
        test_type=PerformanceTestType.FTP_TEST,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(),
    )
    history = PerformanceTestHistory(
        entries=(
            PerformanceHistoryEntry(session=sess1, threshold_analysis=None),
            PerformanceHistoryEntry(session=sess2, threshold_analysis=None),
        )
    )

    provider = StubPerformanceHistoryProvider(history=history)
    adapter = DefaultPerformanceDecisionContextAdapter(provider)
    ctx = adapter.get_context(datetime.now(timezone.utc))

    assert ctx.latest_test_id == "new-02"
    assert ctx.performed_at == gen_at2


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
    perf_adapter = DefaultPerformanceDecisionContextAdapter(EmptyPerformanceTestHistoryProvider())

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
        performance_adapter=DefaultPerformanceDecisionContextAdapter(StubPerformanceHistoryProvider()),
    )

    service = DecisionExecutionService(context_provider=runtime_provider)
    req = DecisionExecutionRequest(decision_id="integ-01", generated_at=gen_at, recorded_at=gen_at)

    result = service.execute(req)

    assert result.record.decision_id == "integ-01"
    assert result.record.policy_result.action == DecisionAction.PROCEED
    assert result.record.recommendation_plan.recommendations[0].code == "proceed_as_planned"
