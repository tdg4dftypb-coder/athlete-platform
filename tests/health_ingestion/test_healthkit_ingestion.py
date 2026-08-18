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


def test_batch_identity_ignores_ephemeral_client_created_at_mutation(context):
    _, database, service = context
    # A. First sync with client_created_at = T1
    b1 = batch(batch_id="batch-id-1", records=[record(external_id="rec-1")])
    b1["client_created_at"] = "2026-08-18T13:00:00+00:00"
    ack1 = service.ingest(b1)
    assert ack1.accepted == 1

    # Retry with same batch_id, device_id, and records, but client_created_at = T2
    b2 = batch(batch_id="batch-id-1", records=[record(external_id="rec-1")])
    b2["client_created_at"] = "2026-08-18T13:05:00+00:00"
    ack2 = service.ingest(b2)
    assert ack2.batch_id == "batch-id-1"
    assert ack2.accepted == 0
    assert ack2.duplicate == 1
    assert ack2.rejected == 0
    assert ack2.safe_to_advance_anchor is True


def test_same_batch_id_with_different_records_triggers_collision_error(context):
    _, database, service = context
    # B. First sync with batch-collision-1
    b1 = batch(batch_id="batch-collision-1", records=[record(external_id="rec-alpha", value=50.0)])
    service.ingest(b1)

    # Different records submitted under same batch_id
    b2 = batch(batch_id="batch-collision-1", records=[record(external_id="rec-beta", value=75.0)])
    with pytest.raises(HealthKitBatchCollisionError):
        service.ingest(b2)


def test_endpoint_returns_200_on_retried_batch_and_409_on_actual_collision(context):
    _, database, service = context
    endpoint = HealthKitIngestionEndpoint(service, "test-token")

    def call_endpoint(payload):
        from io import BytesIO
        raw = json.dumps(payload).encode("utf-8")
        env = {
            "REQUEST_METHOD": "POST",
            "HTTP_AUTHORIZATION": "Bearer test-token",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": BytesIO(raw),
        }
        return endpoint.handle(env)

    # Ingest b1
    b1 = batch(batch_id="batch-ep-1", records=[record(external_id="rec-ep-1")])
    b1["client_created_at"] = "2026-08-18T13:00:00+00:00"
    status1, ack1 = call_endpoint(b1)
    assert status1 == "200 OK"
    assert ack1["accepted"] == 1

    # Retry b1 with different client_created_at -> 200 OK
    b1_retry = batch(batch_id="batch-ep-1", records=[record(external_id="rec-ep-1")])
    b1_retry["client_created_at"] = "2026-08-18T13:10:00+00:00"
    status2, ack2 = call_endpoint(b1_retry)
    assert status2 == "200 OK"
    assert ack2["duplicate"] == 1

    # Same batch_id with different records -> 409 Conflict
    b1_tampered = batch(batch_id="batch-ep-1", records=[record(external_id="rec-ep-2")])
    status3, ack3 = call_endpoint(b1_tampered)
    assert status3 == "409 Conflict"
    assert ack3 == {"error": "batch_identity_collision"}


def test_legacy_hashed_batch_is_idempotently_accepted_without_db_mutation(context):
    _, database, service = context
    endpoint = HealthKitIngestionEndpoint(service, "test-token")

    def call_endpoint(payload):
        from io import BytesIO
        raw = json.dumps(payload).encode("utf-8")
        env = {
            "REQUEST_METHOD": "POST",
            "HTTP_AUTHORIZATION": "Bearer test-token",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": BytesIO(raw),
        }
        return endpoint.handle(env)

    # 1. Ingest initial batch
    rec = record(external_id="legacy-rec-1", value=62.0)
    b_init = batch(batch_id="batch-legacy-1", records=[rec])
    b_init["client_created_at"] = "2026-08-18T12:00:00+00:00"
    status1, ack1 = call_endpoint(b_init)
    assert status1 == "200 OK"
    assert ack1["accepted"] == 1

    # 2. Simulate stored legacy hash that used client_created_at in its digest
    legacy_hash = "sha256:legacy-pre-dd10006-hash"
    database.connection.execute(
        "UPDATE healthkit_ingestion_batches SET payload_hash = ? WHERE batch_id = ?",
        [legacy_hash, "batch-legacy-1"],
    )

    records_count_before = database.connection.execute("SELECT COUNT(*) FROM health_records").fetchone()[0]

    # A. Recreate same semantic batch with different client_created_at
    b_retry = batch(batch_id="batch-legacy-1", records=[rec])
    b_retry["client_created_at"] = "2026-08-18T13:45:00+00:00"
    status2, ack2 = call_endpoint(b_retry)
    assert status2 == "200 OK"
    assert ack2["batch_id"] == "batch-legacy-1"
    assert ack2["accepted"] == 0
    assert ack2["duplicate"] == 1
    assert ack2["rejected"] == 0
    assert ack2["safe_to_advance_anchor"] is True

    # Zero new health_records inserted
    records_count_after = database.connection.execute("SELECT COUNT(*) FROM health_records").fetchone()[0]
    assert records_count_after == records_count_before

    # Stored legacy payload_hash remains 100% unchanged (read-only compatibility path)
    stored_hash_after = database.connection.execute(
        "SELECT payload_hash FROM healthkit_ingestion_batches WHERE batch_id = ?",
        ["batch-legacy-1"],
    ).fetchone()[0]
    assert stored_hash_after == legacy_hash

    # B. Legacy batch with same external_id but changed semantic value -> 409
    rec_tampered_val = record(external_id="legacy-rec-1", value=99.0)
    b_tampered_val = batch(batch_id="batch-legacy-1", records=[rec_tampered_val])
    status3, ack3 = call_endpoint(b_tampered_val)
    assert status3 == "409 Conflict"
    assert ack3 == {"error": "batch_identity_collision"}

    # C. Legacy batch with changed timestamp / metadata -> 409
    rec_tampered_time = record(external_id="legacy-rec-1", value=62.0, start_at="2026-08-18T10:00:00+00:00")
    b_tampered_time = batch(batch_id="batch-legacy-1", records=[rec_tampered_time])
    status4, ack4 = call_endpoint(b_tampered_time)
    assert status4 == "409 Conflict"
    assert ack4 == {"error": "batch_identity_collision"}
