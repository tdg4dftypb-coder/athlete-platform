from datetime import datetime, timedelta

from training.factories.activity_factory import ActivityFactory
from training.ingestion.parsed_activity import (
    ParsedActivity,
    ParsedActivityRecord,
)


def test_factory_builds_activity_with_elapsed_time():

    start = datetime(2026, 7, 30, 8, 0)

    parsed = ParsedActivity(
        start=start,
        end=start + timedelta(seconds=60),
        sport="cycling",
        distance=1.0,
        calories=20,
        records=[
            ParsedActivityRecord(
                timestamp=start + timedelta(seconds=60),
                power=210,
                heart_rate=145,
                cadence=92,
                speed=30.0,
            ),
            ParsedActivityRecord(
                timestamp=start,
                power=200,
                heart_rate=140,
                cadence=90,
                speed=29.0,
            ),
        ],
    )

    activity = ActivityFactory().create(parsed)

    assert activity.duration == 60
    assert [record.elapsed_time for record in activity.records] == [0, 60]
    assert activity.records[0].power == 200.0
    assert activity.records[1].cadence == 92.0


def test_factory_builds_empty_activity():

    start = datetime(2026, 7, 30, 8, 0)

    activity = ActivityFactory().create(
        ParsedActivity(
            start=start,
            end=start,
            sport="cycling",
            distance=0.0,
            calories=0,
            records=[],
        )
    )

    assert activity.duration == 0
    assert activity.records == []
