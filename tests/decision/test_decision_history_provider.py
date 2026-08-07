import duckdb
import pytest

from decision import (
    DecisionAuditRecordDataError,
    DecisionHistory,
    DecisionHistoryProvider,
    DecisionHistoryProviderError,
    DuckDbDecisionAuditRecordRepository,
    EmptyDecisionHistoryProvider,
    RepositoryDecisionHistoryProvider,
)

from tests.decision.test_decision_record_codec import build_sample_record


def test_empty_decision_history_provider():
    provider = EmptyDecisionHistoryProvider()
    history = provider.get_history()

    assert isinstance(history, DecisionHistory)
    assert history.records == ()


def test_repository_decision_history_provider_empty():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    provider = RepositoryDecisionHistoryProvider(repository=repo)

    history = provider.get_history()
    assert isinstance(history, DecisionHistory)
    assert history.records == ()


def test_repository_decision_history_provider_with_records():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    rec1 = build_sample_record("hist-01")
    rec2 = build_sample_record("hist-02")

    repo.save(rec1)
    repo.save(rec2)

    provider = RepositoryDecisionHistoryProvider(repository=repo)
    history = provider.get_history()

    assert len(history.records) == 2
    assert history.records[0] == rec1
    assert history.records[1] == rec2


def test_repository_decision_history_provider_maps_errors():
    class FailingRepo:
        def list_records(self):
            raise DecisionAuditRecordDataError("Data corruption")

    provider = RepositoryDecisionHistoryProvider(repository=FailingRepo())

    with pytest.raises(DecisionHistoryProviderError, match="temporarily unavailable"):
        provider.get_history()


def test_repository_decision_history_provider_propagates_unexpected_errors():
    class UnexpectedRepo:
        def list_records(self):
            raise TypeError("Unexpected type error")

    provider = RepositoryDecisionHistoryProvider(repository=UnexpectedRepo())

    with pytest.raises(TypeError, match="Unexpected type error"):
        provider.get_history()
