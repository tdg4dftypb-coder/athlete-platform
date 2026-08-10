# Activity Calendar read API

`GET /api/v1/activity-calendar` is the canonical bounded read model for native
calendar and day-history presentation. It projects existing persisted facts; it
does not parse activity files or recalculate training metrics.

## Query

- `start_date`: required ISO local date (`YYYY-MM-DD`), inclusive.
- `end_date`: required ISO local date (`YYYY-MM-DD`), inclusive.
- The range must be ordered and contain no more than 62 calendar days.

Invalid or missing parameters return `400`. An available range with no activity
still returns `200` and includes every requested day. A persisted-source failure
returns `503`.

## Response

```json
{
  "start_date": "2026-08-01",
  "end_date": "2026-08-31",
  "timezone": "Europe/Warsaw",
  "days": [
    {
      "date": "2026-08-01",
      "planned_session": {
        "session_id": "plan-id:2026-08-01",
        "kind": "TRAINING",
        "session_type": "ENDURANCE",
        "duration_minutes": 60,
        "target_tss": 50.0
      },
      "activities": [
        {
          "activity_id": "persisted-athlete-memory-event-id",
          "sport": "cycling",
          "start_time": "2026-08-01T08:00:00",
          "duration_seconds": 3600,
          "distance": 25000.0,
          "tss": 55.0,
          "completed": true,
          "status": "good"
        }
      ]
    }
  ]
}
```

`planned_session` is `null` when no persisted plan covers the date. Optional
activity values are JSON `null` when absent from the persisted event. Activities
are ordered by athlete-local start time and stable `activity_id`; days are
chronological.

## Sources and local-day semantics

- Completed activities primarily come from factual `ACTIVITY_RECORDED` Athlete
  Memory events. Existing `WORKOUT_COMPLETED` events remain supported for
  backward compatibility. When both projections carry the same source identity,
  `ACTIVITY_RECORDED` takes deterministic precedence.
  `activity_id` is the existing immutable event `event_id`, suitable for a future
  Activity Detail lookup contract.
- Planned sessions come from the newest persisted `TrainingPlan` applicable to
  each date. The calendar does not generate or reconcile plans.
- The configured athlete timezone is `Europe/Warsaw`. Offset-aware activity
  starts are converted into that zone before day assignment. Existing naive FIT
  timestamps retain the platform's current athlete-local wall-time semantics.
- The persistence query is bounded to the requested interval plus one preceding
  and one following day because Athlete Memory indexes workout completion time
  while calendar grouping uses persisted activity start time.

Historical FIT timestamps in the legacy `workouts` table are naive UTC values.
The explicit backfill emits them with `+00:00`; the calendar then applies the
configured athlete timezone exactly as it does for any offset-aware activity.

There is not yet a public Activity Detail endpoint. Clients may persist and pass
`activity_id`, but should not construct a detail URL until that contract exists.
