"""Deterministic standard-library operational scheduler for background data source sync."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import threading
from typing import Callable

logger = logging.getLogger("athlete.data_sources.scheduler")

ZWIFT_SYNC_INTERVAL_SECONDS = 600  # 10 minutes
INTERVALS_SYNC_INTERVAL_SECONDS = 14400  # 4 hours


class DataSourceSyncScheduler:
    """Manages scheduled background synchronization for automated production data sources."""

    def __init__(
        self,
        *,
        zwift_sync_fn: Callable[[], object] | None = None,
        intervals_sync_fn: Callable[[], object] | None = None,
        zwift_interval_seconds: float = ZWIFT_SYNC_INTERVAL_SECONDS,
        intervals_interval_seconds: float = INTERVALS_SYNC_INTERVAL_SECONDS,
        startup_delay_seconds: float = 1.0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._zwift_sync_fn = zwift_sync_fn
        self._intervals_sync_fn = intervals_sync_fn
        self._zwift_interval = zwift_interval_seconds
        self._intervals_interval = intervals_interval_seconds
        self._startup_delay = startup_delay_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))

        self._zwift_lock = threading.Lock()
        self._intervals_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._shutdown_event.is_set()

    @property
    def zwift_interval_seconds(self) -> float:
        return self._zwift_interval

    @property
    def intervals_interval_seconds(self) -> float:
        return self._intervals_interval

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._shutdown_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="athlete-datasource-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Data source sync scheduler started.")

    def stop(self, timeout: float = 5.0) -> None:
        if self._thread is None:
            return
        self._shutdown_event.set()
        self._thread.join(timeout=timeout)
        self._thread = None
        logger.info("Data source sync scheduler stopped.")

    def sync_zwift_now(self) -> bool:
        if self._zwift_sync_fn is None:
            return False
        if not self._zwift_lock.acquire(blocking=False):
            logger.info("Zwift FIT sync already in progress; skipping overlapping invocation.")
            return False
        try:
            self._zwift_sync_fn()
            return True
        except Exception as exc:
            logger.warning("Scheduled Zwift FIT sync failed safely: %s", exc)
            return False
        finally:
            self._zwift_lock.release()

    def sync_intervals_now(self) -> bool:
        if self._intervals_sync_fn is None:
            return False
        if not self._intervals_lock.acquire(blocking=False):
            logger.info("Intervals.icu sync already in progress; skipping overlapping invocation.")
            return False
        try:
            self._intervals_sync_fn()
            return True
        except Exception as exc:
            logger.warning("Scheduled Intervals.icu sync failed safely: %s", exc)
            return False
        finally:
            self._intervals_lock.release()

    def _run_loop(self) -> None:
        # 1. Startup catch-up after startup delay
        if self._shutdown_event.wait(timeout=self._startup_delay):
            return

        last_zwift = self._now().timestamp()
        last_intervals = self._now().timestamp()

        # Execute catch-up sync on startup
        self.sync_zwift_now()
        self.sync_intervals_now()

        # 2. Main periodic scheduling loop
        while not self._shutdown_event.is_set():
            if self._shutdown_event.wait(timeout=1.0):
                break
            current_time = self._now().timestamp()
            if self._zwift_sync_fn is not None and (current_time - last_zwift) >= self._zwift_interval:
                last_zwift = current_time
                self.sync_zwift_now()
            if self._intervals_sync_fn is not None and (current_time - last_intervals) >= self._intervals_interval:
                last_intervals = current_time
                self.sync_intervals_now()


def create_production_zwift_sync_fn(
    database,
    zwift_source_path: Path | str | None = None,
) -> Callable[[], object]:
    from integrations.zwift_fit.composition import build_zwift_fit_sync_service

    resolved_path = Path(
        zwift_source_path
        or os.environ.get("ZWIFT_ACTIVITY_SOURCE_PATH", "data/zwift_activities")
    )
    service = build_zwift_fit_sync_service(database, resolved_path)

    def run_zwift():
        now = datetime.now(timezone.utc)
        return service.sync(started_at=now)

    return run_zwift


def create_production_intervals_sync_fn(
    intervals_db_path: Path | str | None = None,
    environ: dict | None = None,
) -> Callable[[], object]:
    from integrations.intervals_icu.composition import build_intervals_sync_service
    import duckdb

    target_db_path = str(intervals_db_path or "data/database/intervals_icu.duckdb")

    def run_intervals():
        connection = duckdb.connect(target_db_path)
        try:
            service = build_intervals_sync_service(connection, environ=environ)
            now = datetime.now(timezone.utc)
            return service.sync(started_at=now)
        finally:
            connection.close()

    return run_intervals


def build_production_data_source_scheduler(
    database,
    *,
    zwift_source_path: Path | str | None = None,
    intervals_db_path: Path | str | None = None,
    environ: dict | None = None,
    zwift_interval_seconds: float = ZWIFT_SYNC_INTERVAL_SECONDS,
    intervals_interval_seconds: float = INTERVALS_SYNC_INTERVAL_SECONDS,
    startup_delay_seconds: float = 1.0,
    now: Callable[[], datetime] | None = None,
) -> DataSourceSyncScheduler:
    zwift_fn = create_production_zwift_sync_fn(database, zwift_source_path=zwift_source_path)
    intervals_fn = create_production_intervals_sync_fn(intervals_db_path=intervals_db_path, environ=environ)
    return DataSourceSyncScheduler(
        zwift_sync_fn=zwift_fn,
        intervals_sync_fn=intervals_fn,
        zwift_interval_seconds=zwift_interval_seconds,
        intervals_interval_seconds=intervals_interval_seconds,
        startup_delay_seconds=startup_delay_seconds,
        now=now,
    )
