from copy import deepcopy
from datetime import timedelta
import json

import duckdb
import pytest

from scripts.import_training_plan_continuation import run_import
from training_plan import PlannedSessionKind
from training_plan.continuation_input import (
    TrainingPlanContinuationInputError,
    parse_continuation_specification,
)
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository


WEEKDAYS = (
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
    "FRIDAY", "SATURDAY", "SUNDAY",
)


def training_slot(slot_id="primary", session_type="ENDURANCE"):
    return {
        "slot_id": slot_id,
        "session_type": session_type,
        "duration_minutes": 60,
        "target_tss": 50.0,
        "intensity": "MODERATE",
        "priority": 2,
        "rationale": ["Synthetic operator fixture"],
    }


def native_specification():
    weekdays = []
    for weekday in WEEKDAYS:
        if weekday == "MONDAY":
            weekdays.append({"weekday": weekday, "kind": "REST"})
        else:
            weekdays.append({
                "weekday": weekday,
                "kind": "TRAINING",
                "slots": [training_slot(f"{weekday.lower()}-main")],
            })
    weekdays[-1]["slots"] = [
        training_slot("long-endurance"),
        training_slot("open-water", "SWIM"),
    ]
    weekdays[1]["slots"][0]["session_type"] = "RUNNING"
    return {
        "schema_version": "1.0",
        "plan_id": "plan-synthetic",
        "specification_id": "continuation-synthetic",
        "specification_version": 1,
        "target_horizon_days": 42,
        "extension_days": 14,
        "created_at": "2026-08-13T20:00:00Z",
        "weekdays": weekdays,
    }


def write_input(tmp_path, value=None, name="continuation.json"):
    path = tmp_path / name
    path.write_text(json.dumps(value or native_specification()), encoding="utf-8")
    return path


def test_native_rest_single_and_multi_session_slots_are_canonical():
    value = parse_continuation_specification(json.dumps(native_specification()))
    monday = value.weekdays[0]
    sunday = value.weekdays[-1]
    assert monday.slots[0].kind is PlannedSessionKind.REST
    assert [slot.slot_id for slot in sunday.slots] == ["long-endurance", "open-water"]
    assert {slot.session_type for slot in sunday.slots} == {"ENDURANCE", "SWIM"}
    assert value.weekdays[1].slots[0].session_type == "RUNNING"
    assert (value.target_horizon_days, value.extension_days) == (42, 14)


@pytest.mark.parametrize(
    "mutation, message",
    (
        (lambda value: value["weekdays"][-1]["slots"].append(
            deepcopy(value["weekdays"][-1]["slots"][0])
        ), "duplicate slot_id"),
        (lambda value: value["weekdays"].pop(), "seven"),
        (lambda value: value["weekdays"][-1].update(weekday="MONDAY"), "seven"),
        (lambda value: value["weekdays"][0].update(slots=[training_slot()]), "REST"),
        (lambda value: value["weekdays"][1].update(slots=[]), "non-empty"),
    ),
)
def test_native_weekday_and_slot_invariants_are_rejected(mutation, message):
    value = native_specification()
    mutation(value)
    with pytest.raises(TrainingPlanContinuationInputError, match=message):
        parse_continuation_specification(json.dumps(value))


@pytest.mark.parametrize("field", ("slot_id", "session_type", "target_horizon_days", "extension_days"))
def test_semantic_changes_change_fingerprint(field):
    original = native_specification()
    changed = deepcopy(original)
    if field in ("target_horizon_days", "extension_days"):
        changed[field] += 7
    else:
        changed["weekdays"][1]["slots"][0][field] += "-changed"
    first = parse_continuation_specification(json.dumps(original))
    second = parse_continuation_specification(json.dumps(changed))
    assert first.semantic_fingerprint != second.semantic_fingerprint


def test_adding_a_training_slot_changes_fingerprint():
    original = native_specification()
    changed = deepcopy(original)
    changed["weekdays"][1]["slots"].append(training_slot("second-session", "SWIM"))
    first = parse_continuation_specification(json.dumps(original))
    second = parse_continuation_specification(json.dumps(changed))
    assert first.semantic_fingerprint != second.semantic_fingerprint


def test_created_at_is_audit_only_for_semantic_fingerprint():
    first = parse_continuation_specification(json.dumps(native_specification()))
    changed = native_specification()
    changed["created_at"] = (
        first.created_at + timedelta(hours=1)
    ).isoformat()
    second = parse_continuation_specification(json.dumps(changed))
    assert first.semantic_fingerprint == second.semantic_fingerprint


def test_dry_run_prints_complete_preview_and_performs_zero_writes(tmp_path, capsys):
    database = tmp_path / "plans.duckdb"
    assert run_import(write_input(tmp_path), training_plan_db_path=database) == 0
    output = capsys.readouterr().out
    for expected in (
        "Mode          : DRY RUN",
        "Plan ID       : plan-synthetic",
        "Specification : continuation-synthetic",
        "Version       : 1",
        "Target horizon: 42",
        "Extension days: 14",
        "Created at    : 2026-08-13T20:00:00+00:00",
        "Fingerprint   : sha256:",
        "MONDAY | REST | rest",
        "SUNDAY | TRAINING | long-endurance",
        "SUNDAY | TRAINING | open-water | SWIM",
    ):
        assert expected in output
    assert not database.exists()
    assert not (tmp_path / "plan_adaptation.duckdb").exists()


def test_dry_run_fingerprint_is_stable(tmp_path, capsys):
    source = write_input(tmp_path)
    assert run_import(source, training_plan_db_path=tmp_path / "plans.duckdb") == 0
    first = next(line for line in capsys.readouterr().out.splitlines() if "Fingerprint" in line)
    assert run_import(source, training_plan_db_path=tmp_path / "plans.duckdb") == 0
    second = next(line for line in capsys.readouterr().out.splitlines() if "Fingerprint" in line)
    assert first == second


def test_apply_round_trip_idempotency_and_no_plan_revision(tmp_path, capsys):
    database = tmp_path / "plans.duckdb"
    source = write_input(tmp_path)
    assert run_import(source, apply=True, training_plan_db_path=database) == 0
    assert "persisted" in capsys.readouterr().out
    assert run_import(source, apply=True, training_plan_db_path=database) == 0
    assert "identical no-op" in capsys.readouterr().out
    repository = DuckDbTrainingPlanRepository(database)
    persisted = repository.get_continuation_specification("continuation-synthetic", 1)
    assert persisted == parse_continuation_specification(source.read_text())
    connection = duckdb.connect(str(database), read_only=True)
    assert connection.execute("SELECT count(*) FROM training_plan_revisions").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM training_plans").fetchone()[0] == 0
    connection.close()
    assert {path.name for path in tmp_path.glob("*.duckdb")} == {"plans.duckdb"}


def test_apply_with_audit_timestamp_change_is_idempotent(tmp_path, capsys):
    database = tmp_path / "plans.duckdb"
    assert run_import(write_input(tmp_path), apply=True, training_plan_db_path=database) == 0
    changed = native_specification()
    changed["created_at"] = "2026-08-13T21:00:00Z"
    assert run_import(write_input(tmp_path, changed, "changed.json"), apply=True,
                      training_plan_db_path=database) == 0
    assert "identical no-op" in capsys.readouterr().out


def test_apply_semantic_collision_is_hard_failure(tmp_path, capsys):
    database = tmp_path / "plans.duckdb"
    assert run_import(write_input(tmp_path), apply=True, training_plan_db_path=database) == 0
    changed = native_specification()
    changed["weekdays"][1]["slots"][0]["duration_minutes"] = 99
    assert run_import(write_input(tmp_path, changed, "collision.json"), apply=True,
                      training_plan_db_path=database) == 1
    assert "conflict" in capsys.readouterr().err.lower()


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.update(schema_version="9.0"),
        lambda value: value.update(plan_id=""),
        lambda value: value.update(version=1),
    ),
)
def test_unknown_schema_wrong_plan_and_mismatched_metadata_are_rejected(mutation):
    value = native_specification()
    mutation(value)
    with pytest.raises(TrainingPlanContinuationInputError):
        parse_continuation_specification(json.dumps(value))


def test_malformed_input_is_bounded_cli_error(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text("{not-json", encoding="utf-8")
    database = tmp_path / "plans.duckdb"
    assert run_import(source, apply=True, training_plan_db_path=database) == 2
    captured = capsys.readouterr()
    assert "Continuation import error" in captured.err
    assert "Traceback" not in captured.err
    assert not database.exists()
