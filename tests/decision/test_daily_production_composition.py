"""Tests for Production Daily Decision Runtime Composition Root."""
from datetime import date, datetime, timezone
from pathlib import Path
import pytest
import duckdb

from decision.daily_execution import DailyCoordinatorOutcome, DailyExecutionLedgerState
from decision.daily_production_composition import (
    ProductionDailyDecisionRuntimeContainer,
    create_production_daily_decision_runtime,
)
from decision.persistence import (
    DuckDbDailyExecutionRepository,
    DuckDbDecisionAuditRecordRepository,
)


def test_production_daily_composition_factory_wires_canonical_sources(tmp_path):
    health_db = tmp_path / "health.duckdb"
    bio_db = tmp_path / "biomarkers.duckdb"
    dec_db = tmp_path / "decisions.duckdb"

    container = create_production_daily_decision_runtime(
        health_db_path=health_db,
        biomarkers_db_path=bio_db,
        decisions_db_path=dec_db,
        timezone_name="Europe/Warsaw",
    )

    try:
        assert isinstance(container, ProductionDailyDecisionRuntimeContainer)
        assert container.coordinator is not None
        assert container.daily_repository is not None
        assert container.audit_repository is not None

        # Execute daily run
        res = container.coordinator.run_daily_if_needed()
        assert res.outcome == DailyCoordinatorOutcome.EXECUTED
        assert res.decision_id is not None

        # Verify ledger entry written to target decisions DB
        ledger_rec = container.daily_repository.get_by_run_date(date.today())
        assert ledger_rec is not None
        assert ledger_rec.status == DailyExecutionLedgerState.COMPLETED
        assert ledger_rec.decision_id == res.decision_id

        # Verify audit record written to target decisions DB
        audit_rec = container.audit_repository.get_by_id(res.decision_id)
        assert audit_rec is not None
        assert audit_rec.decision_id == res.decision_id
    finally:
        container.close()


def test_production_daily_composition_resource_lifecycle(tmp_path):
    dec_db = tmp_path / "decisions.duckdb"

    with create_production_daily_decision_runtime(
        decisions_db_path=dec_db,
    ) as container:
        res = container.coordinator.run_daily_if_needed()
        assert res.outcome == DailyCoordinatorOutcome.EXECUTED

    # Ensure connections are released and file can be opened directly
    direct_conn = duckdb.connect(str(dec_db))
    rows = direct_conn.execute("SELECT count(*) FROM daily_decision_executions").fetchone()
    assert rows[0] == 1
    direct_conn.close()
