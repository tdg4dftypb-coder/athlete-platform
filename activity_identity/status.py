"""Read-only, failure-isolated data-source status projection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import ProviderFreshness

CONTRACT_VERSION = "1.0"
TARGETS = {"healthkit": 21600, "intervals_icu": 21600, "zwift_fit": 900}


@dataclass(frozen=True)
class DataSourceStatusReader:
    providers: dict
    now: callable

    def get_payload(self):
        entries = []
        for provider in ("healthkit", "intervals_icu", "zwift_fit"):
            try:
                value = self.providers[provider]()
            except Exception:
                value = ProviderFreshness(provider, None, None, None, "DEGRADED", "status_read_failed")
            target = TARGETS[provider]
            entries.append({
                "provider": provider,
                "operational_status": value.operational_status,
                "freshness_status": value.state(self.now(), target).value,
                "last_attempt_at": _iso(value.last_attempt_at),
                "last_success_at": _iso(value.last_success_at),
                "last_error_code": value.last_error_code,
                "freshness_target_seconds": target,
            })
        return {"contract_version": CONTRACT_VERSION, "providers": entries}


def _iso(value):
    return None if value is None else value.astimezone(timezone.utc).isoformat()


def disabled_status_reader(now=lambda: datetime.now(timezone.utc)):
    return DataSourceStatusReader({name: (lambda name=name: ProviderFreshness(
        name, None, None, None, "DISABLED", None)) for name in TARGETS}, now)
