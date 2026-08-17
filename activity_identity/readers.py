"""Internal provider projections; provider metrics remain in their source stores."""
from datetime import timezone
import json

from .models import SourceActivityObservation


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def read_zwift_observations(connection):
    rows = connection.execute("SELECT candidate_json FROM zwift_fit_artifacts").fetchall()
    result = []
    from datetime import datetime
    for (raw,) in rows:
        item = json.loads(raw)
        result.append(SourceActivityObservation(
            "zwift_fit", item["external_id"], item["sport"],
            datetime.fromisoformat(item["start_at"]), datetime.fromisoformat(item["end_at"]),
            item.get("distance_meters")))
    return tuple(result)


def read_intervals_observations(connection):
    rows = connection.execute("""
      SELECT external_id,sport,start_at,end_at,distance_meters
      FROM intervals_icu_activities WHERE archived=FALSE
    """).fetchall()
    return tuple(SourceActivityObservation("intervals_icu", row[0], row[1],
                 aware(row[2]), aware(row[3]), row[4]) for row in rows)


def read_healthkit_workout_observations(connection):
    rows = connection.execute("""
      SELECT external_id,text_value,start_date,end_date
      FROM health_records WHERE provider='healthkit'
      AND record_type='HKWorkoutTypeIdentifier' AND COALESCE(deleted,FALSE)=FALSE
      AND text_value IS NOT NULL
    """).fetchall()
    from datetime import datetime
    parse = lambda value: value if hasattr(value, "tzinfo") else datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
    return tuple(SourceActivityObservation("healthkit", row[0], row[1],
                 aware(parse(row[2])), aware(parse(row[3]))) for row in rows)
