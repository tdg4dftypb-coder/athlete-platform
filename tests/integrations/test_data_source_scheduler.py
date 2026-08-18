"""Unit and integration tests for background data source synchronization scheduler."""
from datetime import datetime, timedelta, timezone
import threading
import time
from unittest.mock import MagicMock

import pytest

from integrations.scheduler import (
    DataSourceSyncScheduler,
    INTERVALS_SYNC_INTERVAL_SECONDS,
    ZWIFT_SYNC_INTERVAL_SECONDS,
    build_production_data_source_scheduler,
)
from server.app import create_production_dashboard_wsgi_app, create_production_server


def test_import_and_generic_wsgi_app_creation_does_not_start_scheduler(tmp_path):
    # A. scheduler does not start merely by importing/building generic app
    threads_before = threading.enumerate()
    app = create_production_dashboard_wsgi_app(
        health_db_path=tmp_path / "health.duckdb",
        biomarkers_db_path=tmp_path / "bio.duckdb",
        decision_db_path=tmp_path / "dec.duckdb",
        training_plan_db_path=tmp_path / "tp.duckdb",
    )
    assert app is not None
    threads_after = threading.enumerate()
    scheduler_threads = [t for t in threads_after if t.name == "athlete-datasource-scheduler"]
    assert len(scheduler_threads) == 0


def test_production_server_factory_wires_scheduler_without_auto_starting(tmp_path):
    # B. production runtime constructs scheduler with correct configuration
    app, scheduler = create_production_server(
        health_db_path=tmp_path / "health.duckdb",
        biomarkers_db_path=tmp_path / "bio.duckdb",
        decision_db_path=tmp_path / "dec.duckdb",
        training_plan_db_path=tmp_path / "tp.duckdb",
    )
    assert app is not None
    assert scheduler is not None
    assert not scheduler.is_running
    assert scheduler.zwift_interval_seconds == 600
    assert scheduler.intervals_interval_seconds == 14400


def test_scheduler_cadence_constants():
    # C & D. Zwift cadence = 10m (600s), Intervals cadence = 4h (14400s)
    assert ZWIFT_SYNC_INTERVAL_SECONDS == 600
    assert INTERVALS_SYNC_INTERVAL_SECONDS == 14400


def test_startup_catch_up_executes_both_providers_after_delay():
    # E. startup catch-up schedules both providers
    zwift_called = []
    intervals_called = []

    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=lambda: zwift_called.append(datetime.now(timezone.utc)),
        intervals_sync_fn=lambda: intervals_called.append(datetime.now(timezone.utc)),
        zwift_interval_seconds=600,
        intervals_interval_seconds=14400,
        startup_delay_seconds=0.05,
    )

    try:
        scheduler.start()
        assert scheduler.is_running
        time.sleep(0.15)
        assert len(zwift_called) >= 1
        assert len(intervals_called) >= 1
    finally:
        scheduler.stop()
        assert not scheduler.is_running


def test_scheduler_does_not_manage_or_poll_healthkit():
    # F. HealthKit is not polled by the scheduler
    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=lambda: None,
        intervals_sync_fn=lambda: None,
    )
    assert not hasattr(scheduler, "sync_healthkit_now")
    assert not hasattr(scheduler, "_healthkit_sync_fn")


def test_provider_exception_does_not_crash_scheduler_or_halt_other_provider():
    # G. provider exception does not kill scheduler
    zwift_calls = 0
    intervals_calls = 0

    def failing_zwift():
        nonlocal zwift_calls
        zwift_calls += 1
        raise RuntimeError("Simulated Zwift source error")

    def successful_intervals():
        nonlocal intervals_calls
        intervals_calls += 1

    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=failing_zwift,
        intervals_sync_fn=successful_intervals,
        startup_delay_seconds=0.05,
    )

    try:
        scheduler.start()
        time.sleep(0.15)
        # Even though Zwift raised, scheduler remains running and Intervals executed
        assert scheduler.is_running
        assert zwift_calls >= 1
        assert intervals_calls >= 1
    finally:
        scheduler.stop()


def test_same_provider_overlap_is_prevented():
    # H. same-provider overlap is prevented
    started_barrier = threading.Event()
    release_barrier = threading.Event()
    execution_count = 0

    def slow_zwift():
        nonlocal execution_count
        execution_count += 1
        started_barrier.set()
        release_barrier.wait(timeout=2.0)

    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=slow_zwift,
    )

    # Launch first execution in separate thread
    t = threading.Thread(target=scheduler.sync_zwift_now)
    t.start()

    started_barrier.wait(timeout=1.0)
    # Attempt second concurrent execution while first is in progress
    second_result = scheduler.sync_zwift_now()
    assert second_result is False

    release_barrier.set()
    t.join(timeout=1.0)
    assert execution_count == 1


def test_clean_shutdown_terminates_scheduler_thread():
    # I. shutdown is clean
    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=lambda: None,
        intervals_sync_fn=lambda: None,
        startup_delay_seconds=10.0,
    )
    scheduler.start()
    assert scheduler.is_running
    scheduler.stop(timeout=1.0)
    assert not scheduler.is_running


def test_periodic_scheduling_with_fake_clock():
    # Simulated clock advancement
    current_time = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    zwift_runs = []
    intervals_runs = []

    def get_time():
        return current_time

    scheduler = DataSourceSyncScheduler(
        zwift_sync_fn=lambda: zwift_runs.append(current_time),
        intervals_sync_fn=lambda: intervals_runs.append(current_time),
        zwift_interval_seconds=600,
        intervals_interval_seconds=14400,
        startup_delay_seconds=0.01,
        now=get_time,
    )

    try:
        scheduler.start()
        time.sleep(0.05)
        assert len(zwift_runs) == 1
        assert len(intervals_runs) == 1

        # Advance clock by 650 seconds -> trigger Zwift
        current_time += timedelta(seconds=650)
        time.sleep(1.1)
        assert len(zwift_runs) == 2
        assert len(intervals_runs) == 1

        # Advance clock by 14000 seconds -> trigger Intervals
        current_time += timedelta(seconds=14000)
        time.sleep(1.1)
        assert len(zwift_runs) >= 3
        assert len(intervals_runs) == 2
    finally:
        scheduler.stop()
