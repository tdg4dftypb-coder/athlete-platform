from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from activity_identity.composition import DataSourceSyncCoordinator
from activity_identity.matching import match_evidence
from activity_identity.models import (
    FreshnessState, ProviderFreshness, ReconciliationStatus,
    SourceActivityObservation, canonical_activity_id,
)
from activity_identity.persistence import ActivityIdentityRepository, ActivityIdentitySchema
from activity_identity.service import CrossSourceActivityReconciler

NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def obs(provider, external_id, start=NOW, duration=3600, sport="cycling", distance=30000, **kw):
    return SourceActivityObservation(provider, external_id, sport, start,
                                     start + timedelta(seconds=duration), distance, **kw)


@pytest.fixture
def repo(tmp_path):
    c = duckdb.connect(str(tmp_path / "identity.duckdb"))
    ActivityIdentitySchema.create(c); ActivityIdentitySchema.create(c)
    yield c, ActivityIdentityRepository(c)
    c.close()


def test_canonical_id_is_deterministic_and_not_metric_derived():
    assert canonical_activity_id("zwift_fit", "sha256:x") == canonical_activity_id("zwift_fit", "sha256:x")
    assert canonical_activity_id("zwift_fit", "sha256:x") != canonical_activity_id("zwift_fit", "sha256:y")


def test_matching_frozen_boundaries_and_sport():
    zwift = obs("zwift_fit", "z")
    assert match_evidence(zwift, obs("intervals_icu", "i", start=NOW + timedelta(seconds=120)))
    assert not match_evidence(zwift, obs("intervals_icu", "i", start=NOW + timedelta(seconds=121)))
    assert match_evidence(zwift, obs("healthkit", "h", duration=3780))
    assert not match_evidence(zwift, obs("healthkit", "h", duration=3781))
    assert not match_evidence(zwift, obs("healthkit", "h", sport="running"))


def test_explicit_link_precedes_candidate_tolerances():
    zwift = obs("zwift_fit", "z")
    linked = obs("intervals_icu", "i", start=NOW + timedelta(hours=2), sport="running",
                 linked_provider="zwift_fit", linked_external_id="z")
    assert match_evidence(zwift, linked)[0].value == "EXACT_LINK"


def test_zwift_intervals_healthkit_become_one_group(repo):
    _, repository = repo
    records = [obs("zwift_fit", "z"), obs("intervals_icu", "i"), obs("healthkit", "h")]
    result = CrossSourceActivityReconciler(repository).reconcile(records, reconciled_at=NOW)
    assert [item.status for item in result] == [ReconciliationStatus.MATCHED] * 2
    groups = repository.groups()
    assert len(groups) == 1 and {(a.provider, a.external_id) for a in groups[0].aliases} == {
        ("healthkit", "h"), ("intervals_icu", "i")}


@pytest.mark.parametrize("providers", [
    ("zwift_fit",), ("zwift_fit", "intervals_icu"), ("zwift_fit", "healthkit")])
def test_supported_source_combinations_remain_one_activity(repo, providers):
    _, repository = repo
    records = [obs(provider, provider[0]) for provider in providers]
    CrossSourceActivityReconciler(repository).reconcile(records, reconciled_at=NOW)
    assert len(repository.groups()) == 1


def test_two_same_day_rides_remain_two_and_ambiguous_supplemental_is_not_merged(repo):
    _, repository = repo
    z1 = obs("zwift_fit", "z1")
    z2 = obs("zwift_fit", "z2", start=NOW + timedelta(seconds=90))
    supplemental = obs("intervals_icu", "i", start=NOW + timedelta(seconds=45))
    result = CrossSourceActivityReconciler(repository).reconcile([z1, z2, supplemental], reconciled_at=NOW)
    assert len(repository.groups()) == 2
    assert result[0].status is ReconciliationStatus.AMBIGUOUS
    assert all(not group.aliases for group in repository.groups())


def test_late_and_reverse_arrival_promotes_zwift_without_duplicate(repo):
    _, repository = repo
    reconciler = CrossSourceActivityReconciler(repository)
    assert reconciler.reconcile([obs("healthkit", "h"), obs("intervals_icu", "i")], reconciled_at=NOW)
    assert repository.groups() == ()
    later = reconciler.reconcile(
        [obs("healthkit", "h"), obs("intervals_icu", "i"), obs("zwift_fit", "z")],
        reconciled_at=NOW + timedelta(hours=1))
    assert [item.status for item in later] == [ReconciliationStatus.MATCHED] * 2
    retry = reconciler.reconcile(
        [obs("zwift_fit", "z"), obs("healthkit", "h"), obs("intervals_icu", "i")],
        reconciled_at=NOW + timedelta(hours=2))
    assert [item.status for item in retry] == [ReconciliationStatus.ALREADY_MATCHED] * 2
    assert len(repository.groups()) == 1 and len(repository.groups()[0].aliases) == 2


def test_transaction_rollback(repo, monkeypatch):
    connection, repository = repo
    class FailingConnection:
        def execute(self, sql, parameters=None):
            if "activity_reconciliation_audit" in sql: raise RuntimeError("fail")
            return connection.execute(sql, parameters) if parameters is not None else connection.execute(sql)
    repository.connection = FailingConnection()
    with pytest.raises(RuntimeError):
        CrossSourceActivityReconciler(repository).reconcile(
            [obs("zwift_fit", "z"), obs("healthkit", "h")], reconciled_at=NOW)
    assert connection.execute("SELECT COUNT(*) FROM canonical_activity_identities").fetchone() == (0,)


@pytest.mark.parametrize("freshness,expected", [
    (ProviderFreshness("x", NOW, NOW, None, "READY", None), FreshnessState.FRESH),
    (ProviderFreshness("x", NOW, NOW-timedelta(hours=7), None, "READY", None), FreshnessState.STALE),
    (ProviderFreshness("x", None, None, None, "DISABLED", None), FreshnessState.NEVER_SYNCED),
    (ProviderFreshness("x", NOW, None, None, "READY", None), FreshnessState.NEVER_SYNCED),
])
def test_freshness_states(freshness, expected):
    assert freshness.state(NOW, 6 * 3600) is expected


def test_provider_outage_is_isolated():
    calls = []
    def ok(): calls.append("ok")
    def fail(): raise RuntimeError("down")
    states = DataSourceSyncCoordinator({"zwift_fit": ok, "intervals_icu": fail, "healthkit": None}).run()
    assert [state.status for state in states] == ["READY", "DEGRADED", "DISABLED"]
    assert calls == ["ok"]
