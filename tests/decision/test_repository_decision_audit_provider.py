import duckdb
import pytest

from decision import (
    DecisionAuditRecordDataError,
    DecisionAuditRecordProviderError,
    DecisionAuditRecordRepositoryError,
    DuckDbDecisionAuditRecordRepository,
    RepositoryDecisionAuditRecordProvider,
)
from tests.decision.test_decision_record_codec import build_sample_record


def test_repository_audit_provider_get_latest():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    provider = RepositoryDecisionAuditRecordProvider(repository=repo)

    # Empty repo -> None
    assert provider.get_latest_record() is None

    rec = build_sample_record("prov-01")
    repo.save(rec)

    # Fetches saved record
    assert provider.get_latest_record() == rec


def test_repository_audit_provider_maps_repository_errors():
    class FailingRepo:
        def get_latest(self):
            raise DecisionAuditRecordDataError("Corrupted data")

    provider = RepositoryDecisionAuditRecordProvider(repository=FailingRepo())

    with pytest.raises(DecisionAuditRecordProviderError, match="temporarily unavailable"):
        provider.get_latest_record()


def test_repository_audit_provider_propagates_unexpected_errors():
    class UnexpectedRepo:
        def get_latest(self):
            raise TypeError("Unexpected type error")

    provider = RepositoryDecisionAuditRecordProvider(repository=UnexpectedRepo())

    with pytest.raises(TypeError, match="Unexpected type error"):
        provider.get_latest_record()
