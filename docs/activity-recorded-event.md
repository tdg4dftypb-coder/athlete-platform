# ACTIVITY_RECORDED factual event

`ACTIVITY_RECORDED` is the canonical Athlete Memory fact that a physical
activity occurred. It is separate from `WORKOUT_COMPLETED`, which represents a
workout evaluated against an explicit plan and includes execution and feedback.

Schema version 1 contains only persisted facts:

```json
{
  "schema_version": 1,
  "activity": {
    "start": "2026-08-01T22:30:00+00:00",
    "end": "2026-08-01T23:30:00+00:00",
    "sport": "cycling",
    "duration": 3600,
    "distance": 25000.0,
    "calories": 500
  },
  "workout_summary": {
    "tss": 55.0,
    "normalized_power": 210.0,
    "intensity_factor": 0.75
  }
}
```

Optional facts serialize as `null`. Plan snapshots, execution scores, feedback,
and coaching conclusions are forbidden from this contract.

The event metadata uses the established FIT source identity:

- `source_type = fit_file`
- `source_key = sha256:<complete FIT artifact bytes>`

The event store's unique `(event_type, source_type, source_key)` index makes
writes idempotent within each semantic event type while permitting the factual
and rich events for the same FIT identity to coexist. Existing
`WORKOUT_COMPLETED` readers ignore factual events and retain their strict
schema-v1 behavior.

## Historical maintenance command

The command is dry-run by default:

```text
python -m scripts.backfill_activity_facts \
  data/database/health.duckdb \
  /Users/marsm0wa/Documents/Zwift/Activities \
  --start-date 2026-06-10 \
  --end-date 2026-08-10
```

Only an explicitly reviewed run adds `--apply`. The command reads already
analyzed `workouts` rows, hashes retained FIT bytes only for identity, skips
missing or ambiguous artifacts, and never parses FIT or recalculates metrics.

Legacy FIT timestamps are stored as naive UTC in `workouts`; the projection
emits explicit UTC offsets. This preserves Warsaw calendar-day assignment for
offset-aware timestamps, including midnight boundaries.
