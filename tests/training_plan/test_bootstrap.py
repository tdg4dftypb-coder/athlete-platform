from datetime import date
import json

import pytest

from scripts.bootstrap_training_plan import run_bootstrap_training_plan
from training_plan.bootstrap import (
    TrainingPlanBootstrapSpecificationError,
    parse_bootstrap_specification,
)
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository


WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")


def specification():
    sessions = []
    for index, weekday in enumerate(WEEKDAYS):
        if weekday in ("TUESDAY", "THURSDAY", "SUNDAY"):
            sessions.append({
                "weekday": weekday, "kind": "REST", "session_type": None,
                "duration_minutes": 0, "target_tss": 0.0, "intensity": None,
                "priority": 1, "rationale": ["Synthetic recovery day"],
            })
        else:
            sessions.append({
                "weekday": weekday, "kind": "TRAINING", "session_type": "ENDURANCE",
                "duration_minutes": 60 + index, "target_tss": 50.0 + index,
                "intensity": "MODERATE", "priority": 3,
                "rationale": ["Synthetic fixture"],
            })
    return {
        "schema_version": "1.0", "intent_id": "intent-synthetic",
        "plan_id": "plan-synthetic", "start_date": "2026-08-10",
        "end_date": "2026-08-16", "generated_at_utc": "2026-08-09T10:00:00Z",
        "version": 1, "supersedes_plan_id": None, "weekly_sessions": sessions,
    }


def write_spec(tmp_path, value=None):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(value or specification()), encoding="utf-8")
    return path


def test_valid_specification_round_trip_is_deterministic():
    payload = json.dumps(specification())
    first = parse_bootstrap_specification(payload).build_plan()
    second = parse_bootstrap_specification(payload).build_plan()
    assert first == second
    assert first.generated_at.isoformat() == "2026-08-09T10:00:00+00:00"
    assert tuple(item.session_id for item in first.sessions) == tuple(
        f"plan-synthetic:2026-08-{day:02d}" for day in range(10, 17)
    )


def test_bootstrap_losslessly_adapts_single_weekly_slots_to_continuation():
    bootstrap=parse_bootstrap_specification(json.dumps(specification()))
    continuation=bootstrap.build_continuation_specification(
        specification_id="continuation-synthetic",version=1,target_horizon_days=28,extension_days=28,
        created_at=bootstrap.generated_at_utc)
    assert continuation.plan_id==bootstrap.plan_id and continuation.extension_days==28
    assert all(len(day.slots)==1 for day in continuation.weekdays)
    assert continuation.weekdays[0].slots[0].session_type==bootstrap.intent.weekly_sessions[0].session_type


@pytest.mark.parametrize("mutation", ("missing", "duplicate"))
def test_exactly_seven_unique_weekdays_are_required(mutation):
    value = specification()
    if mutation == "missing":
        value["weekly_sessions"].pop()
    else:
        value["weekly_sessions"][-1]["weekday"] = "MONDAY"
    with pytest.raises(TrainingPlanBootstrapSpecificationError):
        parse_bootstrap_specification(json.dumps(value))


def test_rest_and_training_rules_are_delegated_to_domain_models():
    rest = specification()
    rest["weekly_sessions"][1]["duration_minutes"] = 10
    with pytest.raises(TrainingPlanBootstrapSpecificationError, match="REST"):
        parse_bootstrap_specification(json.dumps(rest))
    training = specification()
    training["weekly_sessions"][0]["session_type"] = None
    with pytest.raises(TrainingPlanBootstrapSpecificationError, match="TRAINING"):
        parse_bootstrap_specification(json.dumps(training))


def test_dry_run_prints_preview_and_does_not_create_database(tmp_path, capsys):
    database = tmp_path / "custom.duckdb"
    assert run_bootstrap_training_plan(write_spec(tmp_path), training_plan_db_path=database) == 0
    output = capsys.readouterr().out
    assert "Mode          : DRY RUN" in output
    assert "Plan ID       : plan-synthetic" in output
    assert "2026-08-10 | TRAINING | ENDURANCE" in output
    assert str(database) in output
    assert not database.exists()


def test_apply_persists_covering_plan_and_repeat_is_noop(tmp_path):
    database = tmp_path / "custom.duckdb"
    source = write_spec(tmp_path)
    assert run_bootstrap_training_plan(source, apply=True, training_plan_db_path=database) == 0
    assert run_bootstrap_training_plan(source, apply=True, training_plan_db_path=database) == 0
    repository = DuckDbTrainingPlanRepository(database)
    assert len(repository.list_records()) == 1
    assert repository.get_for_date(date(2026, 8, 11)).plan_id == "plan-synthetic"


def test_conflicting_plan_is_rejected_without_overwrite(tmp_path, capsys):
    database = tmp_path / "plans.duckdb"
    source = write_spec(tmp_path)
    assert run_bootstrap_training_plan(source, apply=True, training_plan_db_path=database) == 0
    changed = specification()
    changed["weekly_sessions"][0]["duration_minutes"] = 99
    changed_source = tmp_path / "changed.json"
    changed_source.write_text(json.dumps(changed), encoding="utf-8")
    assert run_bootstrap_training_plan(changed_source, apply=True, training_plan_db_path=database) == 1
    assert "conflict" in capsys.readouterr().err.lower()
    assert DuckDbTrainingPlanRepository(database).get_by_id("plan-synthetic").sessions[0].duration_minutes == 60


@pytest.mark.parametrize(
    "change",
    (
        lambda value: value.update(start_date="2026-08-17", end_date="2026-08-16"),
        lambda value: value.update(generated_at_utc="2026-08-09T10:00:00"),
    ),
)
def test_invalid_date_range_and_non_utc_generated_at_are_rejected(change):
    value = specification()
    change(value)
    with pytest.raises(TrainingPlanBootstrapSpecificationError):
        parse_bootstrap_specification(json.dumps(value))


def test_malformed_json_is_bounded_cli_error(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text("{not-json", encoding="utf-8")
    database = tmp_path / "plans.duckdb"
    assert run_bootstrap_training_plan(source, apply=True, training_plan_db_path=database) == 2
    captured = capsys.readouterr()
    assert "bootstrap error" in captured.err
    assert "Traceback" not in captured.err
    assert not database.exists()


def test_apply_has_no_decision_runtime_or_other_database_side_effects(tmp_path):
    database = tmp_path / "plans.duckdb"
    assert run_bootstrap_training_plan(
        write_spec(tmp_path), apply=True, training_plan_db_path=database
    ) == 0
    assert {path.name for path in tmp_path.glob("*.duckdb")} == {"plans.duckdb"}
