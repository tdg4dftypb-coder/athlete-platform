from datetime import datetime, timezone
from io import BytesIO
import json

import duckdb
import pytest

from collectors.apple_health.importer import AppleHealthImporter
from core.database import Database
from health_ingestion.http import HealthKitIngestionEndpoint
from health_ingestion.models import HealthKitBatch
from health_ingestion.persistence import (
    HealthKitBatchCollisionError,
    HealthKitIngestionSchema,
    HealthKitRepository,
)
from health_ingestion.service import HealthKitIngestionService
from repositories.health_repository import HealthRepository
from schema.health_schema import HealthSchema


NOW = "2026-08-17T12:00:00+00:00"


def record(external_id="sample-1", **changes):
    value = {
        "external_id": external_id,
        "sample_type": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "start_at": "2026-08-17T06:00:00+00:00",
        "end_at": "2026-08-17T06:00:01+00:00",
        "value": 55.0,
        "unit": "ms",
        "source_name": "Apple Watch",
        "source_bundle_id": "com.apple.health",
        "device_model": "Watch",
        "source_timezone": "Europe/Warsaw",
        "workout_sport": None,
        "deleted": False,
        "updated_at": NOW,
    }
    value.update(changes)
    return value


def batch(batch_id="batch-1", records=None):
    return {
        "contract_version": "1.0",
        "provider": "healthkit",
        "device_id": "device-1",
        "batch_id": batch_id,
        "records": records or [record()],
        "client_created_at": NOW,
    }


@pytest.fixture
def context(tmp_path):
    path = tmp_path / "health.duckdb"
    database = Database(path)
    database.connection.execute(
        """
        CREATE TABLE health_records (
            id BIGINT, record_type VARCHAR, source_name VARCHAR, unit VARCHAR,
            start_date VARCHAR, end_date VARCHAR, numeric_value DOUBLE,
            text_value VARCHAR
        )
        """
    )
    HealthKitIngestionSchema.create(database)
    service = HealthKitIngestionService(HealthKitRepository(database))
    yield path, database, service
    database.close()


def test_valid_batch_is_persisted_and_acknowledged(context):
    _, database, service = context
    ack = service.ingest(batch())
    assert (ack.accepted, ack.duplicate, ack.rejected) == (1, 0, 0)
    assert ack.safe_to_advance_anchor is True
    row = database.connection.execute(
        "SELECT provider, external_id, numeric_value, unit, deleted FROM health_records"
    ).fetchone()
    assert row == ("healthkit", "sample-1", 55.0, "ms", False)


def test_same_batch_retry_is_idempotent(context):
    _, database, service = context
    first = service.ingest(batch())
    second = service.ingest(batch())
    assert first.batch_id == second.batch_id
    assert second.accepted == 0
    assert second.duplicate == 1
    assert database.connection.execute("SELECT COUNT(*) FROM health_records").fetchone() == (1,)


def test_duplicate_sample_uuid_in_new_batch_is_noop(context):
    _, database, service = context
    service.ingest(batch())
    ack = service.ingest(batch("batch-2"))
    assert (ack.accepted, ack.duplicate) == (0, 1)
    assert database.connection.execute("SELECT COUNT(*) FROM health_records").fetchone() == (1,)


def test_same_uuid_with_changed_semantics_is_deterministic_update(context):
    _, database, service = context
    service.ingest(batch())
    ack = service.ingest(batch("batch-2", [record(value=60.0)]))
    assert ack.accepted == 1
    assert database.connection.execute(
        "SELECT numeric_value FROM health_records WHERE external_id = 'sample-1'"
    ).fetchone() == (60.0,)


@pytest.mark.parametrize("change", [
    {"external_id": "bad id"},
    {"start_at": "not-a-time"},
    {"unit": "seconds"},
    {"value": float("inf")},
])
def test_invalid_record_is_partially_rejected_and_blocks_anchor(context, change):
    _, _, service = context
    invalid = record("invalid")
    invalid.update(change)
    ack = service.ingest(batch(records=[record("valid"), invalid]))
    assert (ack.accepted, ack.rejected) == (1, 1)
    assert ack.safe_to_advance_anchor is False


def test_oversize_batch_is_rejected(context):
    _, _, service = context
    with pytest.raises(ValueError, match="1..500"):
        service.ingest(batch(records=[record(f"sample-{i}") for i in range(501)]))


def test_deletion_creates_source_tombstone_and_hides_active_value(context):
    _, database, service = context
    service.ingest(batch())
    deletion = record(
        start_at=None, end_at=None, value=None, unit=None, deleted=True,
    )
    service.ingest(batch("batch-delete", [deletion]))
    assert database.connection.execute(
        "SELECT deleted, numeric_value FROM health_records WHERE external_id = 'sample-1'"
    ).fetchone() == (True, None)


def test_batch_identity_collision_is_hard_failure(context):
    _, _, service = context
    service.ingest(batch())
    with pytest.raises(HealthKitBatchCollisionError):
        service.ingest(batch(records=[record(value=60.0)]))


def endpoint_call(endpoint, payload, token=None):
    raw = json.dumps(payload).encode()
    environ = {
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
        "HTTP_AUTHORIZATION": "" if token is None else f"Bearer {token}",
    }
    return endpoint.handle(environ)


def test_endpoint_requires_configured_valid_auth(context):
    _, _, service = context
    assert endpoint_call(HealthKitIngestionEndpoint(service, None), batch())[0] == "503 Service Unavailable"
    endpoint = HealthKitIngestionEndpoint(service, "secret")
    assert endpoint_call(endpoint, batch())[0] == "401 Unauthorized"
    assert endpoint_call(endpoint, batch(), "wrong")[0] == "401 Unauthorized"
    status, payload = endpoint_call(endpoint, batch(), "secret")
    assert status == "200 OK"
    assert payload["accepted"] == 1


def test_xml_bootstrap_remains_compatible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/raw").mkdir(parents=True)
    xml = tmp_path / "data/raw/export.xml"
    xml.write_text(
        '<HealthData><Record type="HKQuantityTypeIdentifierBodyMass" '
        'sourceName="Health" unit="kg" startDate="2026-08-17 06:00:00 +0000" '
        'endDate="2026-08-17 06:00:01 +0000" value="70"/></HealthData>'
    )
    HealthSchema().create()
    AppleHealthImporter(str(xml)).run()
    connection = duckdb.connect("data/database/health.duckdb", read_only=True)
    assert connection.execute(
        "SELECT record_type, numeric_value, provider FROM health_records"
    ).fetchone() == ("HKQuantityTypeIdentifierBodyMass", 70.0, None)
    connection.close()


def test_existing_health_repository_reads_active_healthkit_record(context, monkeypatch):
    _, database, service = context
    service.ingest(batch())

    class EmptySleepRepository:
        def __init__(self, database=None):
            pass

        def load_records(self):
            return []

    monkeypatch.setattr("repositories.health_repository.SleepRepository", EmptySleepRepository)
    history = HealthRepository(database).load_daily()
    assert len(history) == 1
    assert history[0].hrv == 55.0


def test_health_repository_uses_injected_database_for_sleep(context):
    _, database, service = context
    service.ingest(batch(records=[record(
        external_id="sleep-1",
        sample_type="HKCategoryTypeIdentifierSleepAnalysis",
        start_at="2026-08-16T22:00:00+00:00",
        end_at="2026-08-17T06:00:00+00:00",
        value=1,
        unit="category",
    )]))
    HealthRepository(database).load_daily()


def test_schema_preserves_legacy_rows(context):
    _, database, _ = context
    database.connection.execute(
        "INSERT INTO health_records(record_type, numeric_value) VALUES ('legacy', 1)"
    )
    HealthKitIngestionSchema.create(database)
    assert database.connection.execute(
        "SELECT record_type, numeric_value FROM health_records WHERE provider IS NULL"
    ).fetchone() == ("legacy", 1.0)


def test_optional_fields_present_null_or_omitted_are_accepted(context):
    _, database, service = context
    # A. Optional fields present with values
    rec_full = record(external_id="rec-full", device_model="iPhone14,3", source_timezone="Europe/Warsaw")
    # B. Optional fields explicitly null
    rec_nulls = record(external_id="rec-nulls", device_model=None, source_timezone=None, source_name=None)
    # C. Optional fields omitted by Swift JSONEncoder
    rec_omitted = {
        "external_id": "rec-omitted",
        "sample_type": "HKQuantityTypeIdentifierStepCount",
        "start_at": NOW,
        "end_at": NOW,
        "value": 150.0,
        "unit": "count",
        "deleted": False,
        "updated_at": NOW,
    }
    ack = service.ingest(batch(records=[rec_full, rec_nulls, rec_omitted]))
    assert ack.accepted == 3
    assert ack.rejected == 0
    assert ack.safe_to_advance_anchor is True


def test_missing_required_fields_and_invalid_units_are_rejected(context):
    _, database, service = context
    # D. Missing required value field on active record
    rec_no_val = {
        "external_id": "rec-no-val",
        "sample_type": "HKQuantityTypeIdentifierStepCount",
        "start_at": NOW,
        "end_at": NOW,
        "unit": "count",
        "deleted": False,
        "updated_at": NOW,
    }
    # E. Invalid units/types remain rejected
    rec_bad_unit = record(external_id="rec-bad-unit", sample_type="HKQuantityTypeIdentifierStepCount", unit="ms")
    rec_bad_type = record(external_id="rec-bad-type", sample_type="HKQuantityTypeUnknown")

    ack = service.ingest(batch(records=[rec_no_val, rec_bad_unit, rec_bad_type]))
    assert ack.accepted == 0
    assert ack.rejected == 3
    assert ack.safe_to_advance_anchor is False
    assert set(ack.rejected_external_ids) == {"rec-no-val", "rec-bad-unit", "rec-bad-type"}
