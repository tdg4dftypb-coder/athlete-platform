from datetime import datetime

from training.ingestion.parsed_activity import (
    ParsedActivity,
    ParsedActivityRecord,
)


def test_parsed_activity_is_a_transport_model():

    timestamp = datetime(2026, 7, 30, 8, 0)

    record = ParsedActivityRecord(
        timestamp=timestamp,
        power=250,
        heart_rate=150,
        cadence=90,
        speed=35.0,
    )

    activity = ParsedActivity(
        start=timestamp,
        end=timestamp,
        sport="cycling",
        distance=10.0,
        calories=300,
        records=[record],
    )

    assert activity.records == [record]
    assert activity.sport == "cycling"
