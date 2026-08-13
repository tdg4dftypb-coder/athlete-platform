"""DuckDB repository implementations for TrainingPlan and FinalSessionPrescription."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import threading
from typing import Union

import duckdb

from training_plan.models import PlannedSessionKind, TrainingPlan
from training_plan.continuity import (
    ContinuationSessionSlot, ContinuationWeekday, TrainingPlanContinuationSpecification,
)
from training_plan.intent import Weekday
import json
from training_plan.persistence.codecs import (
    FinalSessionPrescriptionCodec,
    TrainingPlanCodec,
)
from training_plan.prescription import FinalSessionPrescription
from training_plan.repository import (
    FinalSessionPrescriptionRepository,
    TrainingPlanConflictError,
    TrainingPlanDataError,
    TrainingPlanRepository,
    TrainingPlanRepositoryError,
)


class DuckDbTrainingPlanRepository(TrainingPlanRepository):
    """Append-only DuckDB repository for TrainingPlan instances."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._codec = TrainingPlanCodec()
        self._ensure_tables()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        try:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            return duckdb.connect(self._db_path)
        except Exception as e:
            raise TrainingPlanRepositoryError(f"Failed to connect to DuckDB database at '{self._db_path}': {e}") from e

    def _ensure_tables(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS training_plans (
                        plan_id VARCHAR PRIMARY KEY,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        version INTEGER NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        supersedes_plan_id VARCHAR,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL
                    )
                """)
                conn.execute("""CREATE TABLE IF NOT EXISTS training_plan_continuation_specifications (
                    specification_id VARCHAR NOT NULL, version INTEGER NOT NULL, plan_id VARCHAR NOT NULL,
                    semantic_fingerprint VARCHAR NOT NULL, created_at TIMESTAMP NOT NULL,
                    payload_json VARCHAR NOT NULL, PRIMARY KEY(specification_id,version))""")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS training_plan_revisions (
                        plan_id VARCHAR NOT NULL,
                        version INTEGER NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        expected_source_version INTEGER NOT NULL,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL,
                        PRIMARY KEY (plan_id, version)
                    )
                """)
            finally:
                conn.close()

    def save(self, plan: TrainingPlan) -> None:
        if not isinstance(plan, TrainingPlan):
            raise TypeError("plan must be TrainingPlan instance")

        canonical_payload = self._codec.encode(plan)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION")
                row = conn.execute(
                    "SELECT payload_json FROM training_plans WHERE plan_id = ?",
                    [plan.plan_id],
                ).fetchone()

                if row is not None:
                    existing_payload = row[0]
                    if existing_payload != canonical_payload:
                        conn.execute("ROLLBACK")
                        raise TrainingPlanConflictError(
                            f"Plan with id '{plan.plan_id}' already exists with different payload."
                        )
                    conn.execute("ROLLBACK")
                    return

                # Convert naive/aware timestamp for DB storage
                gen_ts = plan.generated_at.astimezone(timezone.utc).replace(tzinfo=None)

                conn.execute(
                    """
                    INSERT INTO training_plans (
                        plan_id, start_date, end_date, version, generated_at,
                        supersedes_plan_id, record_schema_version, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        plan.plan_id,
                        plan.start_date,
                        plan.end_date,
                        plan.version,
                        gen_ts,
                        plan.supersedes_plan_id,
                        self._codec.SCHEMA_VERSION,
                        canonical_payload,
                    ],
                )
                conn.execute("COMMIT")
            except (TrainingPlanConflictError, TrainingPlanDataError):
                raise
            except Exception as e:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise TrainingPlanRepositoryError(f"Failed to save TrainingPlan '{plan.plan_id}': {e}") from e
            finally:
                conn.close()

    def _get_by_id_unlocked(self, conn: duckdb.DuckDBPyConnection, plan_id: str) -> TrainingPlan | None:
        row = conn.execute(
            "SELECT payload_json FROM training_plans WHERE plan_id = ?",
            [plan_id],
        ).fetchone()

        if row is None:
            return None

        return self._codec.decode(row[0])

    def get_by_id(self, plan_id: str) -> TrainingPlan | None:
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    """SELECT payload_json FROM (
                           SELECT version, payload_json FROM training_plans WHERE plan_id = ?
                           UNION ALL
                           SELECT version, payload_json FROM training_plan_revisions WHERE plan_id = ?
                       ) ORDER BY version DESC LIMIT 1""",
                    [plan_id, plan_id],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            finally:
                conn.close()

    def get_by_id_version(self, plan_id: str, version: int) -> TrainingPlan | None:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    """SELECT payload_json FROM (
                           SELECT payload_json FROM training_plans WHERE plan_id = ? AND version = ?
                           UNION ALL
                           SELECT payload_json FROM training_plan_revisions WHERE plan_id = ? AND version = ?
                       ) LIMIT 1""",
                    [plan_id, version, plan_id, version],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            finally:
                conn.close()

    def append_revision(self, expected_source_version: int, plan: TrainingPlan) -> bool:
        """Append N+1 iff latest is N; identical retry is an idempotent no-op."""
        if plan.version != expected_source_version + 1:
            raise TrainingPlanConflictError("revised plan version must equal expected source version + 1")
        payload = self._codec.encode(plan)
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION")
                existing = conn.execute(
                    """SELECT payload_json FROM (
                           SELECT payload_json FROM training_plans WHERE plan_id = ? AND version = ?
                           UNION ALL
                           SELECT payload_json FROM training_plan_revisions WHERE plan_id = ? AND version = ?
                       ) LIMIT 1""",
                    [plan.plan_id, plan.version, plan.plan_id, plan.version],
                ).fetchone()
                if existing is not None:
                    conn.execute("ROLLBACK")
                    if existing[0] == payload:
                        return False
                    raise TrainingPlanConflictError("different revision already exists for plan/version")
                latest = conn.execute(
                    """SELECT MAX(version) FROM (
                           SELECT version FROM training_plans WHERE plan_id = ?
                           UNION ALL SELECT version FROM training_plan_revisions WHERE plan_id = ?
                       )""",
                    [plan.plan_id, plan.plan_id],
                ).fetchone()[0]
                if latest != expected_source_version:
                    conn.execute("ROLLBACK")
                    raise TrainingPlanConflictError("latest plan version does not match expected source version")
                generated = plan.generated_at.astimezone(timezone.utc).replace(tzinfo=None)
                conn.execute(
                    "INSERT INTO training_plan_revisions VALUES (?, ?, ?, ?, ?, ?)",
                    [plan.plan_id, plan.version, generated, expected_source_version, self._codec.SCHEMA_VERSION, payload],
                )
                conn.execute("COMMIT")
                return True
            except TrainingPlanConflictError:
                raise
            except Exception as e:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise TrainingPlanRepositoryError(f"Failed to append TrainingPlan revision: {e}") from e
            finally:
                conn.close()

    def get_latest(self) -> TrainingPlan | None:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute("""
                    SELECT payload_json FROM (
                        SELECT plan_id, version, generated_at, payload_json FROM training_plans
                        UNION ALL SELECT plan_id, version, generated_at, payload_json FROM training_plan_revisions
                    ) ORDER BY generated_at DESC, version DESC, plan_id DESC
                    LIMIT 1
                """).fetchone()

                if row is None:
                    return None
                return self._codec.decode(row[0])
            finally:
                conn.close()

    def get_for_date(self, target_date: date) -> TrainingPlan | None:
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance (not datetime)")

        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    """
                    SELECT payload_json FROM (
                        SELECT plan_id, version, generated_at, start_date, end_date, payload_json FROM training_plans
                        UNION ALL
                        SELECT plan_id, version, generated_at,
                               CAST(json_extract_string(payload_json, '$.start_date') AS DATE) AS start_date,
                               CAST(json_extract_string(payload_json, '$.end_date') AS DATE) AS end_date,
                               payload_json FROM training_plan_revisions
                    ) WHERE start_date <= ? AND end_date >= ?
                    ORDER BY generated_at DESC, version DESC, plan_id DESC
                    LIMIT 1
                    """,
                    [target_date, target_date],
                ).fetchone()

                if row is None:
                    return None
                return self._codec.decode(row[0])
            finally:
                conn.close()

    def list_records(self) -> tuple[TrainingPlan, ...]:
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute("""
                    SELECT payload_json FROM (
                        SELECT plan_id, version, generated_at, payload_json FROM training_plans
                        UNION ALL
                        SELECT plan_id, version, generated_at, payload_json FROM training_plan_revisions
                    ) ORDER BY generated_at ASC, version ASC, plan_id ASC
                """).fetchall()

                return tuple(self._codec.decode(r[0]) for r in rows)
            finally:
                conn.close()

    @staticmethod
    def _encode_spec(value):
        return json.dumps({"schema_version":"1.0","specification_id":value.specification_id,"version":value.version,
            "plan_id":value.plan_id,"target_horizon_days":value.target_horizon_days,"extension_days":value.extension_days,"semantic_fingerprint":value.semantic_fingerprint,
            "created_at":value.created_at.isoformat(),"weekdays":[{"weekday":d.weekday.name,"slots":[{
            "slot_id":s.slot_id,"kind":s.kind.value,"session_type":s.session_type,"duration_minutes":s.duration_minutes,
            "target_tss":s.target_tss,"intensity":s.intensity,"priority":s.priority,"rationale":list(s.rationale)} for s in d.slots]}
            for d in value.weekdays]},sort_keys=True,separators=(",",":"))

    @staticmethod
    def _decode_spec(payload):
        try:
            d=json.loads(payload)
            if d["schema_version"]!="1.0": raise ValueError("unsupported schema")
            days=tuple(ContinuationWeekday(Weekday[x["weekday"]],tuple(ContinuationSessionSlot(
                s["slot_id"],PlannedSessionKind(s["kind"]),s["session_type"],s["duration_minutes"],s["target_tss"],
                s["intensity"],s["priority"],tuple(s["rationale"])) for s in x["slots"])) for x in d["weekdays"])
            return TrainingPlanContinuationSpecification(d["specification_id"],d["version"],d["plan_id"],d["target_horizon_days"],d["extension_days"],
                days,d["semantic_fingerprint"],datetime.fromisoformat(d["created_at"]))
        except Exception as e: raise TrainingPlanDataError(f"Failed to decode continuation specification: {e}") from e

    def save_continuation_specification(self,value):
        payload=self._encode_spec(value)
        with self._lock:
            conn=self._get_connection()
            try:
                row=conn.execute("SELECT payload_json FROM training_plan_continuation_specifications WHERE specification_id=? AND version=?",
                    [value.specification_id,value.version]).fetchone()
                if row:
                    old=json.loads(row[0]); new=json.loads(payload); old.pop("created_at",None); new.pop("created_at",None)
                    if old!=new: raise TrainingPlanConflictError("continuation specification collision")
                    return False
                conn.execute("INSERT INTO training_plan_continuation_specifications VALUES (?,?,?,?,?,?)",
                    [value.specification_id,value.version,value.plan_id,value.semantic_fingerprint,
                     value.created_at.astimezone(timezone.utc).replace(tzinfo=None),payload]); return True
            finally: conn.close()

    def get_continuation_specification(self,specification_id,version):
        with self._lock:
            conn=self._get_connection()
            try:
                row=conn.execute("SELECT payload_json FROM training_plan_continuation_specifications WHERE specification_id=? AND version=?",
                                 [specification_id,version]).fetchone()
                return None if row is None else self._decode_spec(row[0])
            finally: conn.close()

    def get_latest_continuation_specification_for_plan(self,plan_id):
        with self._lock:
            conn=self._get_connection()
            try:
                row=conn.execute("SELECT payload_json FROM training_plan_continuation_specifications WHERE plan_id=? ORDER BY version DESC,specification_id DESC LIMIT 1",[plan_id]).fetchone()
                return None if row is None else self._decode_spec(row[0])
            finally: conn.close()


class DuckDbFinalSessionPrescriptionRepository(FinalSessionPrescriptionRepository):
    """Append-only DuckDB repository for FinalSessionPrescription instances."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._codec = FinalSessionPrescriptionCodec()
        self._ensure_tables()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        try:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            return duckdb.connect(self._db_path)
        except Exception as e:
            raise TrainingPlanRepositoryError(f"Failed to connect to DuckDB database at '{self._db_path}': {e}") from e

    def _ensure_tables(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS final_session_prescriptions (
                        prescription_id VARCHAR PRIMARY KEY,
                        plan_id VARCHAR NOT NULL,
                        planned_session_id VARCHAR NOT NULL,
                        decision_id VARCHAR NOT NULL,
                        session_date DATE NOT NULL,
                        disposition VARCHAR NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        reconciliation_policy_version VARCHAR NOT NULL,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL,
                        UNIQUE (planned_session_id, decision_id)
                    )
                """)
            finally:
                conn.close()

    def save(self, prescription: FinalSessionPrescription) -> None:
        if not isinstance(prescription, FinalSessionPrescription):
            raise TypeError("prescription must be FinalSessionPrescription instance")

        canonical_payload = self._codec.encode(prescription)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION")

                # Check prescription_id conflict or natural (planned_session_id, decision_id) conflict
                row = conn.execute(
                    "SELECT prescription_id, payload_json FROM final_session_prescriptions WHERE prescription_id = ? OR (planned_session_id = ? AND decision_id = ?)",
                    [
                        prescription.prescription_id,
                        prescription.source_session.session_id,
                        prescription.decision_id,
                    ],
                ).fetchone()

                if row is not None:
                    existing_payload = row[1]
                    if existing_payload != canonical_payload:
                        conn.execute("ROLLBACK")
                        raise TrainingPlanConflictError(
                            f"Prescription with id '{prescription.prescription_id}' or natural key ({prescription.source_session.session_id}, {prescription.decision_id}) already exists with different payload."
                        )
                    conn.execute("ROLLBACK")
                    return

                gen_ts = prescription.generated_at.astimezone(timezone.utc).replace(tzinfo=None)

                conn.execute(
                    """
                    INSERT INTO final_session_prescriptions (
                        prescription_id, plan_id, planned_session_id, decision_id,
                        session_date, disposition, generated_at, reconciliation_policy_version,
                        record_schema_version, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        prescription.prescription_id,
                        prescription.plan_id,
                        prescription.source_session.session_id,
                        prescription.decision_id,
                        prescription.date,
                        prescription.disposition.value,
                        gen_ts,
                        prescription.reconciliation_policy_version,
                        self._codec.SCHEMA_VERSION,
                        canonical_payload,
                    ],
                )
                conn.execute("COMMIT")
            except (TrainingPlanConflictError, TrainingPlanDataError):
                raise
            except Exception as e:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise TrainingPlanRepositoryError(f"Failed to save FinalSessionPrescription '{prescription.prescription_id}': {e}") from e
            finally:
                conn.close()

    def get_by_id(self, prescription_id: str) -> FinalSessionPrescription | None:
        if not isinstance(prescription_id, str) or not prescription_id.strip():
            raise ValueError("prescription_id must be non-empty string")

        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT payload_json FROM final_session_prescriptions WHERE prescription_id = ?",
                    [prescription_id],
                ).fetchone()

                if row is None:
                    return None
                return self._codec.decode(row[0])
            finally:
                conn.close()

    def get_latest(self) -> FinalSessionPrescription | None:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute("""
                    SELECT payload_json FROM final_session_prescriptions
                    ORDER BY generated_at DESC, prescription_id DESC
                    LIMIT 1
                """).fetchone()

                if row is None:
                    return None
                return self._codec.decode(row[0])
            finally:
                conn.close()

    def list_records(self) -> tuple[FinalSessionPrescription, ...]:
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute("""
                    SELECT payload_json FROM final_session_prescriptions
                    ORDER BY generated_at ASC, prescription_id ASC
                """).fetchall()

                return tuple(self._codec.decode(r[0]) for r in rows)
            finally:
                conn.close()
