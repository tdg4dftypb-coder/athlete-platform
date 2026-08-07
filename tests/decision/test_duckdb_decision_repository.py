from datetime import datetime, timedelta, timezone
import duckdb
import pytest

from decision import (
    AthleteDecisionContextBuilder,
    ContextDataStatus,
    DecisionAuditRecordBuilder,
    DecisionAuditRecordConflictError,
    DecisionAuditRecordDataError,
    DecisionAuditRecordRepositoryError,
    DecisionExecutionService,
    DecisionPolicyV2,
    DefaultRecoveryDecisionContextAdapter,
    DefaultTrainingDecisionContextAdapter,
    DuckDbDecisionAuditRecordRepository,
    PerformanceDecisionContext,
    RecommendationPlanBuilder,
    RecoveryDecisionContext,
    TrainingDecisionContext,
    create_decision_runtime_workflow,
)
from tests.decision.test_decision_record_codec import build_sample_record


@pytest.fixture
def in_memory_repo():
    conn = duckdb.connect(":memory:")
    return DuckDbDecisionAuditRecordRepository(conn=conn)


def test_duckdb_repo_save_and_get_by_id(in_memory_repo):
    rec = build_sample_record("repo-01")
    in_memory_repo.save(rec)

    fetched = in_memory_repo.get_by_id("repo-01")
    assert fetched == rec


def test_duckdb_repo_idempotent_save(in_memory_repo):
    rec = build_sample_record("repo-idempotent")
    in_memory_repo.save(rec)
    # Save identical record again (no-op)
    in_memory_repo.save(rec)

    records = in_memory_repo.list_records()
    assert len(records) == 1
    assert records[0] == rec


def test_duckdb_repo_conflict_error_on_different_payload(in_memory_repo):
    t1 = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 6, 11, 0, 0, tzinfo=timezone.utc)

    rec1 = build_sample_record("repo-conflict", gen_at=t1)
    rec2 = build_sample_record("repo-conflict", gen_at=t2)

    in_memory_repo.save(rec1)

    with pytest.raises(DecisionAuditRecordConflictError, match="already exists with different payload"):
        in_memory_repo.save(rec2)

    # Original record remains untouched
    assert in_memory_repo.get_by_id("repo-conflict") == rec1


def test_duckdb_repo_get_latest_ordering(in_memory_repo):
    assert in_memory_repo.get_latest() is None

    t1 = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 6, 11, 0, 0, tzinfo=timezone.utc)

    rec1 = build_sample_record("rec-t1", gen_at=t1)
    rec2 = build_sample_record("rec-t2", gen_at=t2)
    rec3 = build_sample_record("rec-t3", gen_at=t3)

    in_memory_repo.save(rec1)
    in_memory_repo.save(rec2)
    in_memory_repo.save(rec3)

    latest = in_memory_repo.get_latest()
    assert latest == rec2  # t2 is newest (12:00)


def test_duckdb_repo_list_records_oldest_to_newest(in_memory_repo):
    assert in_memory_repo.list_records() == ()

    t1 = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 6, 11, 0, 0, tzinfo=timezone.utc)

    rec1 = build_sample_record("rec-t1", gen_at=t1)
    rec2 = build_sample_record("rec-t2", gen_at=t2)
    rec3 = build_sample_record("rec-t3", gen_at=t3)

    in_memory_repo.save(rec2)
    in_memory_repo.save(rec1)
    in_memory_repo.save(rec3)

    listed = in_memory_repo.list_records()
    assert len(listed) == 3
    assert listed == (rec1, rec3, rec2)  # t1 (10:00) < t3 (11:00) < t2 (12:00)


def test_duckdb_repo_metadata_mismatch_raises_data_error(in_memory_repo):
    rec = build_sample_record("meta-mismatch")
    in_memory_repo.save(rec)

    # Tamper metadata row directly in SQL
    in_memory_repo._conn.execute(
        "UPDATE decision_audit_records SET action = 'INVALID_ACTION' WHERE decision_id = 'meta-mismatch'"
    )

    with pytest.raises(DecisionAuditRecordDataError, match="Metadata action mismatch"):
        in_memory_repo.get_by_id("meta-mismatch")


def test_duckdb_repo_generated_at_tampering_raises_data_error(in_memory_repo):
    rec = build_sample_record("genat-mismatch")
    in_memory_repo.save(rec)

    in_memory_repo._conn.execute(
        "UPDATE decision_audit_records SET generated_at = '2099-01-01 00:00:00' WHERE decision_id = 'genat-mismatch'"
    )

    with pytest.raises(DecisionAuditRecordDataError, match="Metadata generated_at mismatch"):
        in_memory_repo.get_by_id("genat-mismatch")


def test_duckdb_repo_recorded_at_tampering_raises_data_error(in_memory_repo):
    rec = build_sample_record("recat-mismatch")
    in_memory_repo.save(rec)

    in_memory_repo._conn.execute(
        "UPDATE decision_audit_records SET recorded_at = '2099-01-01 00:00:00' WHERE decision_id = 'recat-mismatch'"
    )

    with pytest.raises(DecisionAuditRecordDataError, match="Metadata recorded_at mismatch"):
        in_memory_repo.get_by_id("recat-mismatch")



def test_file_database_round_trip(tmp_path):
    db_file = tmp_path / "test_decision.duckdb"
    repo1 = DuckDbDecisionAuditRecordRepository(db_path=str(db_file))
    rec = build_sample_record("file-db-01")
    repo1.save(rec)

    # Re-open repository on the same file database
    repo2 = DuckDbDecisionAuditRecordRepository(db_path=str(db_file))
    fetched = repo2.get_by_id("file-db-01")
    assert fetched == rec
    assert repo2.get_latest() == rec



def test_workflow_save_read_integration(in_memory_repo):
    from tests.decision.test_decision_runtime_composition import (
        CountingMorningBriefingProvider,
        CountingPerformanceProvider,
    )
    from morning_briefing.input_models import MorningBriefingInput, RecoveryBriefingInput, TrainingBriefingInput

    gen_at = datetime.now(timezone.utc)
    mb_input = MorningBriefingInput(
        generated_at=gen_at,
        recovery=RecoveryBriefingInput(score=85, status="ready", summary=None, is_stale=False),
        training=TrainingBriefingInput(title="Endurance", description=None, duration_minutes=90, intensity="moderate", is_available=True),
        biomarkers=None,
    )

    workflow = create_decision_runtime_workflow(
        morning_briefing_provider=CountingMorningBriefingProvider(mb_input),
        performance_test_provider=CountingPerformanceProvider(),
    )

    # 1. Run workflow
    result = workflow.run()
    record = result.record

    # 2. Save explicitly to repo
    in_memory_repo.save(record)

    # 3. Read back by ID
    retrieved = in_memory_repo.get_by_id(record.decision_id)
    assert retrieved == record
    assert in_memory_repo.get_latest() == record


def test_architecture_import_isolation():
    import importlib
    import inspect

    mod_repo = importlib.import_module('decision.repository')
    source_repo = inspect.getsource(mod_repo)
    assert 'duckdb' not in source_repo
    assert 'server' not in source_repo

    mod_codec = importlib.import_module('decision.persistence.record_codec')
    source_codec = inspect.getsource(mod_codec)
    assert 'duckdb' not in source_codec
    assert 'server' not in source_codec

    mod_duck = importlib.import_module('decision.persistence.duckdb_repository')
    source_duck = inspect.getsource(mod_duck)
    prohibited = ['server', 'DecisionPolicyV2', 'DecisionRuntimeWorkflow', 'morning_briefing', 'performance_lab', 'workout']
    for line in source_duck.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited:
                assert p not in line_clean, f"Prohibited import '{p}' in duckdb_repository.py: {line_clean}"
