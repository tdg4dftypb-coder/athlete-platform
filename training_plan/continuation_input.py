"""Parser for the explicit operator-owned continuation specification input."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from training_plan.continuity import (
    ContinuationSessionSlot,
    ContinuationWeekday,
    TrainingPlanContinuationSpecification,
)
from training_plan.intent import Weekday
from training_plan.models import PlannedSessionKind


CONTINUATION_INPUT_SCHEMA_VERSION = "1.0"


class TrainingPlanContinuationInputError(ValueError):
    """The native continuation JSON cannot form a canonical specification."""


def parse_continuation_specification(
    payload: str,
) -> TrainingPlanContinuationSpecification:
    """Parse structure, then delegate semantic validation to domain objects."""
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise TypeError("root must be an object")
        _require_keys(
            data,
            {
                "schema_version", "plan_id", "specification_id",
                "specification_version", "target_horizon_days", "extension_days",
                "created_at", "weekdays",
            },
            "root",
        )
        if data["schema_version"] != CONTINUATION_INPUT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version '{data['schema_version']}'"
            )
        raw_weekdays = data["weekdays"]
        if not isinstance(raw_weekdays, list):
            raise TypeError("weekdays must be a list")

        weekdays = tuple(_parse_weekday(item) for item in raw_weekdays)
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if (
            created_at.tzinfo is None
            or created_at.utcoffset() != timezone.utc.utcoffset(created_at)
        ):
            raise ValueError("created_at must be timezone-aware UTC")

        return TrainingPlanContinuationSpecification.create(
            specification_id=data["specification_id"],
            version=data["specification_version"],
            plan_id=data["plan_id"],
            target_horizon_days=data["target_horizon_days"],
            extension_days=data["extension_days"],
            weekdays=weekdays,
            created_at=created_at,
        )
    except TrainingPlanContinuationInputError:
        raise
    except Exception as error:
        raise TrainingPlanContinuationInputError(
            f"Invalid Training Plan continuation specification: {error}"
        ) from error


def _parse_weekday(data) -> ContinuationWeekday:
    if not isinstance(data, dict):
        raise TypeError("weekday definition must be an object")
    weekday = Weekday[data["weekday"]]
    kind = PlannedSessionKind(data["kind"])
    if kind is PlannedSessionKind.REST:
        _require_keys(data, {"weekday", "kind"}, "REST weekday")
        if "slots" in data:
            raise ValueError("REST weekday must not define slots")
        slots = (
            ContinuationSessionSlot(
                "rest", PlannedSessionKind.REST, None, 0, 0.0, None, 1, ()
            ),
        )
    else:
        _require_keys(data, {"weekday", "kind", "slots"}, "TRAINING weekday")
        raw_slots = data["slots"]
        if not isinstance(raw_slots, list):
            raise TypeError("TRAINING slots must be a list")
        slots = tuple(_parse_training_slot(slot) for slot in raw_slots)
    return ContinuationWeekday(weekday, slots)


def _parse_training_slot(slot) -> ContinuationSessionSlot:
    if not isinstance(slot, dict):
        raise TypeError("TRAINING slot must be an object")
    _require_keys(
        slot,
        {
            "slot_id", "session_type", "duration_minutes", "target_tss",
            "intensity", "priority", "rationale",
        },
        "TRAINING slot",
    )
    return ContinuationSessionSlot(
        slot["slot_id"],
        PlannedSessionKind.TRAINING,
        slot["session_type"],
        slot["duration_minutes"],
        slot["target_tss"],
        slot["intensity"],
        slot["priority"],
        tuple(slot["rationale"]),
    )


def _require_keys(data: dict, expected: set[str], label: str) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"{label} fields mismatch; missing={missing}, unknown={unknown}")
