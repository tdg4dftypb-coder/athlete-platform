import json
from datetime import datetime, timedelta, timezone

from activity_identity.models import ProviderFreshness
from activity_identity.status import DataSourceStatusReader
from server.app import create_dashboard_wsgi_app

NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def call(reader):
    status = None
    def start(value, headers):
        nonlocal status
        status = value
    body = b"".join(create_dashboard_wsgi_app(data_source_status_reader=reader)(
        {"PATH_INFO": "/api/v1/data-sources/status", "REQUEST_METHOD": "GET"}, start))
    return status, json.loads(body)


def test_all_three_states_and_safe_contract_are_returned():
    reader = DataSourceStatusReader({
        "healthkit": lambda: ProviderFreshness("healthkit", NOW, NOW, "anchor:opaque", "READY", None),
        "intervals_icu": lambda: ProviderFreshness("intervals_icu", NOW, NOW-timedelta(hours=7), "scan", "READY", None),
        "zwift_fit": lambda: ProviderFreshness("zwift_fit", None, None, None, "DISABLED", None),
    }, lambda: NOW)
    status, payload = call(reader)
    assert status == "200 OK" and payload["contract_version"] == "1.0"
    assert [p["provider"] for p in payload["providers"]] == ["healthkit", "intervals_icu", "zwift_fit"]
    assert [p["freshness_status"] for p in payload["providers"]] == ["FRESH", "STALE", "NEVER_SYNCED"]
    raw = json.dumps(payload)
    assert not any(secret in raw for secret in ("API_KEY", "athlete_id", "/Users/", "HRV", "sleep"))


def test_one_provider_read_failure_is_isolated_and_does_not_trigger_sync():
    calls = []
    def health(): calls.append("read"); return ProviderFreshness("healthkit", None, None, None, "READY", None)
    def broken(): raise RuntimeError("secret /Users/private")
    reader = DataSourceStatusReader({"healthkit": health, "intervals_icu": broken,
                                     "zwift_fit": lambda: ProviderFreshness("zwift_fit", NOW, NOW, None, "READY", None)},
                                    lambda: NOW)
    _, payload = call(reader)
    assert calls == ["read"]
    assert payload["providers"][1]["operational_status"] == "DEGRADED"
    assert payload["providers"][1]["last_error_code"] == "status_read_failed"


def test_default_endpoint_is_200_disabled_never_synced_and_read_only():
    status, payload = call(None) if False else (None, None)
    app = create_dashboard_wsgi_app()
    captured = []
    body = b"".join(app({"PATH_INFO":"/api/v1/data-sources/status","REQUEST_METHOD":"GET"},
                         lambda status, headers: captured.append(status)))
    value = json.loads(body)
    assert captured == ["200 OK"]
    assert all(item["operational_status"] == "DISABLED" for item in value["providers"])
    assert all(item["freshness_status"] == "NEVER_SYNCED" for item in value["providers"])
