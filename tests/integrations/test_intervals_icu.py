from datetime import date, datetime, timezone
import logging

import duckdb
import pytest

from integrations.intervals_icu.client import IntervalsClient, TransportResponse
from integrations.intervals_icu.errors import (
    AuthenticationFailure, ConfigurationMissing, MalformedResponse,
    PaginationFailure, PersistenceFailure, RateLimited,
)
from integrations.intervals_icu.models import IntervalsActivity, IntervalsConfiguration, Sport
from integrations.intervals_icu.persistence import IntervalsRepository, IntervalsSchema
from integrations.intervals_icu.service import IntervalsSyncService

NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def activity(identifier="i1", **changes):
    value = {
        "id": identifier, "start_date": "2026-08-16T08:00:00Z", "type": "Ride",
        "elapsed_time": 3600, "distance": 30000, "icu_training_load": 70,
        "icu_intensity": 82, "average_heartrate": 145, "average_watts": 190,
        "weighted_average_watts": 210, "average_cadence": 88,
        "icu_sync_date": "2026-08-16T10:00:00Z",
    }
    value.update(changes)
    return value


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(status=200, body=b"[]", headers=None):
    return TransportResponse(status, body, headers or {})


def client(responses, sleeps=None):
    transport = Transport(responses)
    delays = [] if sleeps is None else sleeps
    value = IntervalsClient(IntervalsConfiguration("i123", "top-secret"), transport,
                            sleeper=delays.append)
    return value, transport, delays


def test_configuration_is_typed_disabled_and_secret_is_not_logged(caplog):
    assert not IntervalsConfiguration.from_environment({}).enabled
    with pytest.raises(ConfigurationMissing):
        IntervalsClient(IntervalsConfiguration(None, None))
    configured, _, _ = client([response(401)])
    with caplog.at_level(logging.DEBUG), pytest.raises(AuthenticationFailure):
        configured.list_activities(date(2026, 8, 1), date(2026, 8, 2))
    assert "top-secret" not in caplog.text


def test_valid_single_page_uses_real_read_only_endpoint_and_basic_auth():
    import json
    configured, transport, _ = client([response(body=json.dumps([activity()]).encode())])
    records = configured.list_activities(date(2026, 8, 1), date(2026, 8, 17))
    assert records[0].external_id == "i1"
    assert records[0].intervals_external_tss == 70
    url, headers, timeout = transport.calls[0]
    assert url.endswith("/athlete/i123/activities?oldest=2026-08-01&newest=2026-08-17")
    assert headers["Authorization"].startswith("Basic ") and timeout == 15


def test_empty_page_and_unknown_optional_fields_are_valid():
    configured, _, _ = client([response(), response(body=__import__("json").dumps([
        activity(type="NovelSport", future_field={"ignored": True})
    ]).encode())])
    assert configured.list_activities(date.today(), date.today()) == ()
    assert configured.list_activities(date.today(), date.today())[0].sport is Sport.OTHER


@pytest.mark.parametrize("body", [b"{", b"{}", b"[{}]", b'[{"id":"i1"}]'])
def test_malformed_or_required_field_missing_is_rejected(body):
    configured, _, _ = client([response(body=body)])
    with pytest.raises(MalformedResponse):
        configured.list_activities(date.today(), date.today())


def test_timeout_5xx_and_429_retry_are_bounded():
    from integrations.intervals_icu.errors import ProviderUnavailable
    configured, transport, delays = client([
        ProviderUnavailable("timeout"), response(503), response(200),
    ])
    assert configured.list_activities(date.today(), date.today()) == ()
    assert len(transport.calls) == 3 and delays == [1, 2]
    configured, transport, delays = client([response(429, headers={"Retry-After": "2"}), response()])
    assert configured.list_activities(date.today(), date.today()) == ()
    assert delays == [2.0]


def test_401_does_not_retry_and_exhausted_429_is_typed():
    configured, transport, _ = client([response(401)])
    with pytest.raises(AuthenticationFailure):
        configured.list_activities(date.today(), date.today())
    assert len(transport.calls) == 1
    configured, transport, _ = client([response(429), response(429), response(429)])
    with pytest.raises(RateLimited):
        configured.list_activities(date.today(), date.today())
    assert len(transport.calls) == 3


@pytest.fixture
def repository(tmp_path):
    connection = duckdb.connect(str(tmp_path / "intervals.duckdb"))
    IntervalsSchema.create(connection)
    IntervalsSchema.create(connection)
    yield connection, IntervalsRepository(connection)
    connection.close()


def normalized(**changes):
    payload = activity(**changes)
    return IntervalsActivity.from_provider(payload)


def persist(repo, records, suffix="1", before=None, after=NOW):
    return repo.persist_slice(records, started_at=NOW, completed_at=NOW,
                              watermark_before=before, watermark_after=after,
                              sync_id="sync-" + suffix)


def test_persistence_insert_noop_update_tombstone_and_watermark(repository):
    connection, repo = repository
    assert persist(repo, [normalized()]) == (1, 0, 0, 0)
    assert persist(repo, [normalized()], "2", NOW, NOW) == (0, 0, 1, 0)
    assert persist(repo, [normalized(distance=31000)], "3", NOW, NOW) == (0, 1, 0, 0)
    assert persist(repo, [normalized(archived=True)], "4", NOW, NOW) == (0, 1, 0, 1)
    assert repo.watermark() == NOW
    assert connection.execute("SELECT COUNT(*) FROM intervals_icu_activities").fetchone() == (1,)


def test_failed_transaction_does_not_advance_watermark(repository, monkeypatch):
    _, repo = repository
    persist(repo, [normalized()], after=NOW)
    original = repo.semantic_hash
    monkeypatch.setattr(repo, "semantic_hash", lambda record: (_ for _ in ()).throw(RuntimeError()))
    with pytest.raises(PersistenceFailure):
        persist(repo, [normalized(id="i2")], "2", NOW, datetime(2026, 8, 18, tzinfo=timezone.utc))
    monkeypatch.setattr(repo, "semantic_hash", original)
    assert repo.watermark() == NOW


class RecordingClient:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.windows = []

    def list_activities(self, oldest, newest):
        self.windows.append((oldest, newest))
        value = next(self.pages)
        if isinstance(value, Exception):
            raise value
        return tuple(value)


def test_sync_bootstrap_is_90_days_time_paged_and_deterministic(repository):
    _, repo = repository
    provider = RecordingClient([[], [], [normalized()]])
    result = IntervalsSyncService(provider, repo).sync(started_at=NOW)
    assert provider.windows == [
        (date(2026, 5, 19), date(2026, 6, 18)),
        (date(2026, 6, 19), date(2026, 7, 19)),
        (date(2026, 7, 20), date(2026, 8, 17)),
    ]
    assert (result.fetched, result.inserted, result.provider_status) == (1, 1, "SUCCESS")


def test_incremental_overlap_late_update_no_duplicates_and_empty_sync(repository):
    _, repo = repository
    persist(repo, [normalized()], after=datetime(2026, 8, 16, 10, tzinfo=timezone.utc))
    changed = normalized(distance=32000, icu_sync_date="2026-08-17T08:00:00Z")
    provider = RecordingClient([[changed, changed]])
    result = IntervalsSyncService(provider, repo).sync(started_at=NOW)
    assert provider.windows[0][0] == date(2026, 8, 9)
    assert (result.fetched, result.updated) == (2, 1)
    empty = RecordingClient([[]])
    result = IntervalsSyncService(empty, repo).sync(
        started_at=datetime(2026, 8, 18, tzinfo=timezone.utc)
    )
    assert result.fetched == 0 and result.watermark_after == datetime(2026, 8, 18, tzinfo=timezone.utc)


def test_page_failure_retains_watermark(repository):
    from integrations.intervals_icu.errors import ProviderUnavailable
    _, repo = repository
    provider = RecordingClient([[normalized()], ProviderUnavailable("down")])
    with pytest.raises(PaginationFailure):
        IntervalsSyncService(provider, repo).sync(started_at=NOW)
    assert repo.watermark() is None


def test_source_ownership_is_explicit_and_canonical_tables_untouched(repository):
    connection, repo = repository
    connection.execute("CREATE TABLE training_plans(id VARCHAR)")
    connection.execute("CREATE TABLE activity_events(kind VARCHAR)")
    connection.execute("CREATE TABLE platform_load(metric VARCHAR, value DOUBLE)")
    connection.execute("INSERT INTO training_plans VALUES ('canonical')")
    connection.execute("INSERT INTO activity_events VALUES ('EXISTING')")
    connection.execute("INSERT INTO platform_load VALUES ('CTL', 42)")
    persist(repo, [normalized(icu_training_load=99)])
    assert connection.execute("SELECT * FROM training_plans").fetchall() == [("canonical",)]
    assert connection.execute("SELECT * FROM activity_events").fetchall() == [("EXISTING",)]
    assert connection.execute("SELECT * FROM platform_load").fetchall() == [("CTL", 42.0)]
    columns = {row[1] for row in connection.execute("PRAGMA table_info('intervals_icu_activities')").fetchall()}
    assert "intervals_external_tss" in columns and not {"tss", "ctl", "atl", "tsb"} & columns
