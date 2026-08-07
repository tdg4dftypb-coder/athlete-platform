import pytest

from decision import (
    DecisionHistory,
    DecisionHistoryBuilder,
    DecisionHistorySerializer,
)
from tests.decision.test_decision_record_codec import build_sample_record


def test_decision_history_serializer_empty():
    serializer = DecisionHistorySerializer()
    history = DecisionHistory(records=())

    serialized = serializer.serialize(history)

    assert serialized == {
        "records": [],
        "count": 0,
    }


def test_decision_history_serializer_with_records():
    serializer = DecisionHistorySerializer()
    rec1 = build_sample_record("ser-hist-01")
    rec2 = build_sample_record("ser-hist-02")
    history = DecisionHistoryBuilder().build((rec1, rec2))

    serialized = serializer.serialize(history)

    assert serialized["count"] == 2
    assert isinstance(serialized["records"], list)
    assert len(serialized["records"]) == 2
    assert serialized["records"][0]["decision_id"] == "ser-hist-01"
    assert serialized["records"][1]["decision_id"] == "ser-hist-02"


def test_decision_history_serializer_invalid_input():
    serializer = DecisionHistorySerializer()

    with pytest.raises(TypeError, match="history must be DecisionHistory"):
        serializer.serialize("invalid")
