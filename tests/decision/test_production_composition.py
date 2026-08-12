from pathlib import Path
import duckdb
import pytest

from decision.persistence import DuckDbDecisionAuditRecordRepository
from decision.production_composition import (
    ProductionDecisionRuntimeContainer,
    create_production_decision_runtime_application,
)
from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
from performance_lab.provider import EmptyPerformanceTestHistoryProvider
from scripts.run_decision_runtime import run_decision_runtime
from server.app import create_production_dashboard_wsgi_app
from tests.server.test_decision_intelligence_v2_endpoint import make_request


def test_production_composition_factory_wires_real_sources(tmp_path):
    health_db = tmp_path / "health.duckdb"
    bio_db = tmp_path / "biomarkers.duckdb"
    dec_db = tmp_path / "decisions.duckdb"

    container = create_production_decision_runtime_application(
        health_db_path=health_db,
        biomarkers_db_path=bio_db,
        decisions_db_path=dec_db,
    )

    try:
        assert isinstance(container, ProductionDecisionRuntimeContainer)
        workflow = container.app.workflow

        # Production workflow uses ProductionMorningBriefingInputProvider
        mb_provider = workflow._runtime_workflow._execution_service._context_provider._recovery_adapter._provider
        assert isinstance(mb_provider, ProductionMorningBriefingInputProvider)

        # Performance provider defaults to EmptyPerformanceTestHistoryProvider (UNAVAILABLE)
        perf_provider = workflow._runtime_workflow._execution_service._context_provider._performance_adapter._provider
        assert isinstance(perf_provider, EmptyPerformanceTestHistoryProvider)

        # Single run creates exactly 1 decision audit record in DuckDB
        res = workflow.run()
        assert res.record is not None

        repo = DuckDbDecisionAuditRecordRepository(db_path=str(dec_db))
        assert repo.get_latest() == res.record
        assert repo.get_by_id(res.record.decision_id) == res.record
    finally:
        container.close()


def test_resource_cleanup_handles_close(tmp_path):
    health_db = tmp_path / "health.duckdb"
    bio_db = tmp_path / "biomarkers.duckdb"
    dec_db = tmp_path / "decisions.duckdb"

    with create_production_decision_runtime_application(
        health_db_path=health_db,
        biomarkers_db_path=bio_db,
        decisions_db_path=dec_db,
    ) as container:
        assert container.database is not None
        assert container.biomarkers_context is not None

    # Verify context manager closes connections without throwing errors
    with pytest.raises(duckdb.Error):
        container.database.connection.execute("SELECT 1")


def test_decision_get_endpoints_are_strictly_read_only(tmp_path):
    health_db = tmp_path / "health.duckdb"
    bio_db = tmp_path / "biomarkers.duckdb"
    dec_db = tmp_path / "decisions.duckdb"

    # Seed 1 record via production runtime
    with create_production_decision_runtime_application(
        health_db_path=health_db,
        biomarkers_db_path=bio_db,
        decisions_db_path=dec_db,
    ) as container:
        container.app.workflow.run()

    app = create_production_dashboard_wsgi_app(
        health_db_path=health_db,
        biomarkers_db_path=bio_db,
        decision_db_path=dec_db,
        activity_reconciliation_db_path=tmp_path / "reconciliation.duckdb",
    )

    repo = DuckDbDecisionAuditRecordRepository(db_path=str(dec_db))
    initial_count = len(repo.list_records())
    assert initial_count == 1

    # Perform multiple GET /latest and GET /history requests
    status1, resp1, body1 = make_request(app, method="GET", path="/api/v1/decision-intelligence/latest")
    assert status1 == 200

    status2, resp2, body2 = make_request(app, method="GET", path="/api/v1/decision-intelligence/history")
    assert status2 == 200

    status3, resp3, body3 = make_request(app, method="GET", path="/api/v1/decision-intelligence/latest")
    assert status3 == 200

    # CRITICAL INVARIANT: Record count MUST remain unchanged
    after_count = len(repo.list_records())
    assert after_count == initial_count == 1


def test_production_composition_default_paths_point_to_repo_root():
    from decision.persistence.paths import PROJECT_ROOT, get_default_decisions_db_path

    default_dec_path = get_default_decisions_db_path()
    assert default_dec_path == PROJECT_ROOT / "data" / "database" / "decisions.duckdb"
    assert "decision/data" not in str(default_dec_path).replace("\\", "/")
