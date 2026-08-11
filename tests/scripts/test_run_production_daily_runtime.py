from datetime import date
from types import SimpleNamespace

import pytest

from production_runtime.models import RuntimeStatus
from production_runtime.diagnostics import RuntimeResumability
from scripts.run_production_daily_runtime import run_production_daily_runtime


class Coordinator:
    def __init__(self, status):
        self.status = status
        self.target = None
    def run_new_attempt(self, target):
        self.target = target
        return SimpleNamespace(
            runtime_id="runtime-1", target_local_date=target, status=self.status,
            revision=10, phases=(), decision_id="d", training_plan_id="p",
            prescription_id="r", morning_briefing_available=True, warnings=(), failure=None,
        )
    def resume_attempt(self, runtime_id):
        self.resumed = runtime_id
        return self.run_new_attempt(self.target or date(2026, 8, 11))


class Reader:
    def __init__(self, snapshot):
        self.snapshot = snapshot
    def get_latest_for_date(self, target):
        return self.snapshot


class FailingReader:
    def get_latest_for_date(self, target):
        raise RuntimeError("audit unavailable")


def operational(status, resumability, runtime_id="runtime-existing"):
    return SimpleNamespace(
        status=status, resumability=resumability, runtime_id=runtime_id,
        target_local_date=date(2026, 8, 11), revision=10,
    )


def test_candidate_cli_success(capsys):
    coordinator = Coordinator(RuntimeStatus.COMPLETED)
    assert run_production_daily_runtime(date(2026, 8, 11), coordinator=coordinator) == 0
    assert "runtime-1" in capsys.readouterr().out


def test_candidate_cli_partial_is_nonzero_without_traceback(capsys):
    coordinator = Coordinator(RuntimeStatus.PARTIAL)
    assert run_production_daily_runtime(date(2026, 8, 11), coordinator=coordinator) == 1
    assert "Traceback" not in capsys.readouterr().out


def test_scheduler_no_attempt_starts_new():
    coordinator = Coordinator(RuntimeStatus.COMPLETED)
    assert run_production_daily_runtime(
        date(2026, 8, 11), coordinator=coordinator, operation="scheduled",
        status_reader=Reader(None),
    ) == 0
    assert coordinator.target == date(2026, 8, 11)


def test_scheduler_running_resumes_same_attempt():
    coordinator = Coordinator(RuntimeStatus.COMPLETED)
    coordinator.target = date(2026, 8, 11)
    assert run_production_daily_runtime(
        coordinator=coordinator, target_date=coordinator.target, operation="scheduled",
        status_reader=Reader(operational(RuntimeStatus.RUNNING, RuntimeResumability.RESUME_SAME_ATTEMPT)),
    ) == 0
    assert coordinator.resumed == "runtime-existing"


def test_scheduler_completed_is_successful_noop(capsys):
    coordinator = Coordinator(RuntimeStatus.FAILED)
    assert run_production_daily_runtime(
        date(2026, 8, 11), coordinator=coordinator, operation="scheduled",
        status_reader=Reader(operational(RuntimeStatus.COMPLETED, RuntimeResumability.NO_ACTION)),
    ) == 0
    assert coordinator.target is None
    assert "already completed" in capsys.readouterr().out


@pytest.mark.parametrize("status", (RuntimeStatus.PARTIAL, RuntimeStatus.FAILED))
def test_scheduler_terminal_failure_requires_operator_action(status, capsys):
    assert run_production_daily_runtime(
        date(2026, 8, 11), coordinator=Coordinator(RuntimeStatus.COMPLETED),
        operation="scheduled",
        status_reader=Reader(operational(status, RuntimeResumability.START_NEW_ATTEMPT)),
    ) == 1
    assert "operator action" in capsys.readouterr().err


def test_scheduler_unsupported_state_requires_operator_action(capsys):
    assert run_production_daily_runtime(
        date(2026, 8, 11), coordinator=Coordinator(RuntimeStatus.COMPLETED),
        operation="scheduled",
        status_reader=Reader(operational(RuntimeStatus.RUNNING, RuntimeResumability.NOT_SUPPORTED)),
    ) == 1
    assert "operator action" in capsys.readouterr().err


def test_scheduler_audit_unavailable_is_nonzero_without_traceback(capsys):
    assert run_production_daily_runtime(
        date(2026, 8, 11), coordinator=Coordinator(RuntimeStatus.COMPLETED),
        operation="scheduled", status_reader=FailingReader(),
    ) == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert "Traceback" not in captured.err
