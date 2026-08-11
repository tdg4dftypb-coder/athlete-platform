from datetime import date
from types import SimpleNamespace

from production_runtime.models import RuntimeStatus
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


def test_candidate_cli_success(capsys):
    coordinator = Coordinator(RuntimeStatus.COMPLETED)
    assert run_production_daily_runtime(date(2026, 8, 11), coordinator=coordinator) == 0
    assert "runtime-1" in capsys.readouterr().out


def test_candidate_cli_partial_is_nonzero_without_traceback(capsys):
    coordinator = Coordinator(RuntimeStatus.PARTIAL)
    assert run_production_daily_runtime(date(2026, 8, 11), coordinator=coordinator) == 1
    assert "Traceback" not in capsys.readouterr().out
