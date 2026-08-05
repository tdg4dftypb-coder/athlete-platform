"""
DuckDB Implementation of LaboratoryRepository Protocol Port.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple
import duckdb

from biomarkers.deletion import DeletionMode, DeletionResult
from biomarkers.errors import ImportRunActivationError, ReportNotFoundError
from biomarkers.models import (
    BiomarkerValueType,
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReferenceRange,
    LaboratoryReport,
    NormalizationStatus,
    PlatformMessageLevel,
    VerificationStatus,
)
from biomarkers.persistence.migrations import run_migrations


def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def from_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DuckDBLaboratoryRepository:
    """
    Thread-safe DuckDB adapter for LaboratoryRepository protocol.
    Enforces atomic transactions, aware UTC datetimes, schema migration, and tombstone deletion semantics.
    """

    def __init__(
        self,
        db_path: str = "data/database/biomarkers.duckdb",
        conn: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> None:
        self._lock = threading.Lock()
        if conn is not None:
            self._conn = conn
        else:
            p = Path(db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(p))

        run_migrations(self._conn)

    def close(self) -> None:
        """Idempotently closes DuckDB connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _ensure_open(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            raise RuntimeError("Repository connection is closed.")
        return self._conn

    def is_source_tombstoned(self, source_document_hash: str) -> bool:
        if not source_document_hash:
            return False
        doc_hash = source_document_hash.strip()
        with self._lock:
            conn = self._ensure_open()
            tombstone = conn.execute(
                "SELECT tombstone_id FROM laboratory_tombstones WHERE source_document_hash = ?",
                [doc_hash],
            ).fetchone()
            return tombstone is not None

    def find_report_by_source_hash(self, source_document_hash: str) -> Optional[LaboratoryReport]:
        if not source_document_hash:
            return None
        doc_hash = source_document_hash.strip()

        with self._lock:
            conn = self._ensure_open()
            tombstone = conn.execute(
                "SELECT tombstone_id FROM laboratory_tombstones WHERE source_document_hash = ?",
                [doc_hash],
            ).fetchone()
            if tombstone:
                return None

            row = conn.execute(
                """
                SELECT report_id, collected_at, reported_at, laboratory_name, source_type, source_document_hash, created_at
                FROM laboratory_reports
                WHERE source_document_hash = ?
                """,
                [doc_hash],
            ).fetchone()

            if not row:
                return None

            return self._row_to_report(row)

    def get_report(self, report_id: str) -> Optional[LaboratoryReport]:
        if not report_id:
            return None
        r_id = report_id.strip()

        with self._lock:
            conn = self._ensure_open()
            row = conn.execute(
                """
                SELECT report_id, collected_at, reported_at, laboratory_name, source_type, source_document_hash, created_at
                FROM laboratory_reports
                WHERE report_id = ?
                """,
                [r_id],
            ).fetchone()

            if not row:
                return None

            return self._row_to_report(row)

    def get_all_reports(self) -> Tuple[LaboratoryReport, ...]:
        with self._lock:
            conn = self._ensure_open()
            rows = conn.execute(
                """
                SELECT report_id, collected_at, reported_at, laboratory_name, source_type, source_document_hash, created_at
                FROM laboratory_reports
                ORDER BY created_at ASC
                """
            ).fetchall()
            return tuple(self._row_to_report(row) for row in rows)

    def get_import_runs(self, report_id: str) -> Tuple[LaboratoryImportRun, ...]:
        if not report_id:
            return ()
        r_id = report_id.strip()

        with self._lock:
            conn = self._ensure_open()
            rows = conn.execute(
                """
                SELECT import_run_id, report_id, parser_version, extractor_version, registry_version,
                       unit_rules_version, started_at, completed_at, status, active, warnings_json
                FROM laboratory_import_runs
                WHERE report_id = ?
                ORDER BY started_at ASC
                """,
                [r_id],
            ).fetchall()

            runs: List[LaboratoryImportRun] = []
            for row in rows:
                run_id = row[0]
                obs_rows = conn.execute(
                    """
                    SELECT observation_id, import_run_id, report_id, report_row_index, observation_source_fingerprint,
                           raw_name, raw_value, raw_unit, canonical_code, normalization_status, requires_review,
                           alias_match_confidence, value_type, numeric_value, text_value, qualitative_value,
                           inequality_operator, range_low, range_high, normalized_value, normalized_unit,
                           ref_low, ref_high, ref_text, ref_unit, ref_lab_provided, laboratory_flag,
                           laboratory_provided_critical_flag, collected_at, reported_at, laboratory_name,
                           source_type, source_document_hash, name_confidence, value_confidence, unit_confidence,
                           reference_confidence, extraction_confidence, overall_confidence, verification_status,
                           trend_status, training_context_signal, platform_message_level, is_possible_duplicate, metadata_json
                    FROM laboratory_observations
                    WHERE import_run_id = ?
                    ORDER BY report_row_index ASC
                    """,
                    [run_id],
                ).fetchall()

                observations = tuple(self._row_to_observation(obs_r) for obs_r in obs_rows)
                runs.append(self._row_to_import_run(row, observations))

            return tuple(runs)

    def get_active_import_run(self, report_id: str) -> Optional[LaboratoryImportRun]:
        if not report_id:
            return None
        r_id = report_id.strip()

        with self._lock:
            conn = self._ensure_open()
            row = conn.execute(
                """
                SELECT import_run_id, report_id, parser_version, extractor_version, registry_version,
                       unit_rules_version, started_at, completed_at, status, active, warnings_json
                FROM laboratory_import_runs
                WHERE report_id = ? AND active = TRUE
                """,
                [r_id],
            ).fetchone()

            if not row:
                return None

            run_id = row[0]
            obs_rows = conn.execute(
                """
                SELECT observation_id, import_run_id, report_id, report_row_index, observation_source_fingerprint,
                       raw_name, raw_value, raw_unit, canonical_code, normalization_status, requires_review,
                       alias_match_confidence, value_type, numeric_value, text_value, qualitative_value,
                       inequality_operator, range_low, range_high, normalized_value, normalized_unit,
                       ref_low, ref_high, ref_text, ref_unit, ref_lab_provided, laboratory_flag,
                       laboratory_provided_critical_flag, collected_at, reported_at, laboratory_name,
                       source_type, source_document_hash, name_confidence, value_confidence, unit_confidence,
                       reference_confidence, extraction_confidence, overall_confidence, verification_status,
                       trend_status, training_context_signal, platform_message_level, is_possible_duplicate, metadata_json
                    FROM laboratory_observations
                    WHERE import_run_id = ?
                    ORDER BY report_row_index ASC
                """,
                [run_id],
            ).fetchall()

            observations = tuple(self._row_to_observation(obs_r) for obs_r in obs_rows)
            return self._row_to_import_run(row, observations)

    def find_observations_for_duplicate_check(
        self,
        canonical_code: str,
        collected_at: datetime,
        normalized_value: Optional[float],
        exclude_report_id: str,
    ) -> Tuple[LaboratoryObservation, ...]:
        if not canonical_code or collected_at is None:
            return ()

        target_code = canonical_code.strip().lower()
        target_date_str = (collected_at.date() if isinstance(collected_at, datetime) else collected_at).isoformat()

        with self._lock:
            conn = self._ensure_open()
            query = """
                SELECT o.observation_id, o.import_run_id, o.report_id, o.report_row_index, o.observation_source_fingerprint,
                       o.raw_name, o.raw_value, o.raw_unit, o.canonical_code, o.normalization_status, o.requires_review,
                       o.alias_match_confidence, o.value_type, o.numeric_value, o.text_value, o.qualitative_value,
                       o.inequality_operator, o.range_low, o.range_high, o.normalized_value, o.normalized_unit,
                       o.ref_low, o.ref_high, o.ref_text, o.ref_unit, o.ref_lab_provided, o.laboratory_flag,
                       o.laboratory_provided_critical_flag, o.collected_at, o.reported_at, o.laboratory_name,
                       o.source_type, o.source_document_hash, o.name_confidence, o.value_confidence, o.unit_confidence,
                       o.reference_confidence, o.extraction_confidence, o.overall_confidence, o.verification_status,
                       o.trend_status, o.training_context_signal, o.platform_message_level, o.is_possible_duplicate, o.metadata_json
                FROM laboratory_observations o
                JOIN laboratory_import_runs r ON o.import_run_id = r.import_run_id
                WHERE r.active = TRUE
                  AND o.report_id != ?
                  AND LOWER(o.canonical_code) = ?
                  AND strftime(o.collected_at, '%Y-%m-%d') = ?
            """
            params = [exclude_report_id, target_code, target_date_str]
            obs_rows = conn.execute(query, params).fetchall()

            matching: List[LaboratoryObservation] = []
            for r in obs_rows:
                obs = self._row_to_observation(r)
                if normalized_value is not None and (obs.normalized_value is not None or obs.numeric_value is not None):
                    obs_val = obs.normalized_value if obs.normalized_value is not None else obs.numeric_value
                    if abs(obs_val - normalized_value) < 1e-5:
                        matching.append(obs)
                elif normalized_value is None:
                    matching.append(obs)

            return tuple(matching)

    def save_report_with_import_run(
        self, report: LaboratoryReport, import_run: LaboratoryImportRun
    ) -> None:
        r_id = report.report_id.strip()
        run_id = import_run.import_run_id.strip()

        with self._lock:
            conn = self._ensure_open()
            conn.execute("BEGIN TRANSACTION")
            try:
                # 1. Upsert Report
                conn.execute(
                    """
                    INSERT INTO laboratory_reports (report_id, collected_at, reported_at, laboratory_name, source_type, source_document_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        collected_at = EXCLUDED.collected_at,
                        reported_at = EXCLUDED.reported_at,
                        laboratory_name = EXCLUDED.laboratory_name,
                        source_type = EXCLUDED.source_type,
                        source_document_hash = EXCLUDED.source_document_hash,
                        created_at = EXCLUDED.created_at
                    """,
                    [
                        r_id,
                        to_naive_utc(report.collected_at),
                        to_naive_utc(report.reported_at),
                        report.laboratory_name,
                        report.source_type,
                        report.source_document_hash,
                        to_naive_utc(report.created_at),
                    ],
                )

                # 2. Delete old observations for run_id before upserting import_run
                conn.execute("DELETE FROM laboratory_observations WHERE import_run_id = ?", [run_id])

                # 3. Upsert Import Run
                warnings_json = json.dumps(list(import_run.warnings))
                conn.execute(
                    """
                    INSERT INTO laboratory_import_runs (import_run_id, report_id, parser_version, extractor_version, registry_version, unit_rules_version, started_at, completed_at, status, active, warnings_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(import_run_id) DO UPDATE SET
                        report_id = EXCLUDED.report_id,
                        parser_version = EXCLUDED.parser_version,
                        extractor_version = EXCLUDED.extractor_version,
                        registry_version = EXCLUDED.registry_version,
                        unit_rules_version = EXCLUDED.unit_rules_version,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        status = EXCLUDED.status,
                        active = EXCLUDED.active,
                        warnings_json = EXCLUDED.warnings_json
                    """,
                    [
                        run_id,
                        r_id,
                        import_run.parser_version,
                        import_run.extractor_version,
                        import_run.registry_version,
                        import_run.unit_rules_version,
                        to_naive_utc(import_run.started_at),
                        to_naive_utc(import_run.completed_at),
                        import_run.status.value,
                        import_run.active,
                        warnings_json,
                    ],
                )

                # 4. Insert new observations
                for obs in import_run.observations:
                    ref_low = obs.laboratory_reference_range.low if obs.laboratory_reference_range else None
                    ref_high = obs.laboratory_reference_range.high if obs.laboratory_reference_range else None
                    ref_text = obs.laboratory_reference_range.text if obs.laboratory_reference_range else None
                    ref_unit = obs.laboratory_reference_range.unit if obs.laboratory_reference_range else None
                    ref_lab_provided = obs.laboratory_reference_range.laboratory_provided if obs.laboratory_reference_range else None

                    conn.execute(
                        """
                        INSERT INTO laboratory_observations (
                            observation_id, import_run_id, report_id, report_row_index, observation_source_fingerprint,
                            raw_name, raw_value, raw_unit, canonical_code, normalization_status, requires_review,
                            alias_match_confidence, value_type, numeric_value, text_value, qualitative_value,
                            inequality_operator, range_low, range_high, normalized_value, normalized_unit,
                            ref_low, ref_high, ref_text, ref_unit, ref_lab_provided, laboratory_flag,
                            laboratory_provided_critical_flag, collected_at, reported_at, laboratory_name,
                            source_type, source_document_hash, name_confidence, value_confidence, unit_confidence,
                            reference_confidence, extraction_confidence, overall_confidence, verification_status,
                            trend_status, training_context_signal, platform_message_level, is_possible_duplicate, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            obs.observation_id,
                            run_id,
                            r_id,
                            obs.report_row_index,
                            obs.observation_source_fingerprint,
                            obs.raw_name,
                            obs.raw_value,
                            obs.raw_unit,
                            obs.canonical_code,
                            obs.normalization_status.value,
                            obs.requires_review,
                            obs.alias_match_confidence,
                            obs.value_type.value,
                            obs.numeric_value,
                            obs.text_value,
                            obs.qualitative_value,
                            obs.inequality_operator,
                            obs.range_low,
                            obs.range_high,
                            obs.normalized_value,
                            obs.normalized_unit,
                            ref_low,
                            ref_high,
                            ref_text,
                            ref_unit,
                            ref_lab_provided,
                            obs.laboratory_flag,
                            obs.laboratory_provided_critical_flag,
                            to_naive_utc(obs.collected_at),
                            to_naive_utc(obs.reported_at),
                            obs.laboratory_name,
                            obs.source_type,
                            obs.source_document_hash,
                            obs.name_confidence,
                            obs.value_confidence,
                            obs.unit_confidence,
                            obs.reference_confidence,
                            obs.extraction_confidence,
                            obs.overall_confidence,
                            obs.verification_status.value,
                            obs.trend_status,
                            obs.training_context_signal,
                            obs.platform_message_level.value,
                            obs.is_possible_duplicate,
                            json.dumps(dict(obs.metadata)),
                        ],
                    )

                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def activate_import_run(self, report_id: str, import_run_id: str) -> None:
        r_id = report_id.strip()
        run_id = import_run_id.strip()

        with self._lock:
            conn = self._ensure_open()
            conn.execute("BEGIN TRANSACTION")
            try:
                rep = conn.execute("SELECT report_id FROM laboratory_reports WHERE report_id = ?", [r_id]).fetchone()
                if not rep:
                    raise ReportNotFoundError(f"Report '{r_id}' not found for run activation.")

                target_run = conn.execute("SELECT import_run_id FROM laboratory_import_runs WHERE report_id = ? AND import_run_id = ?", [r_id, run_id]).fetchone()
                if not target_run:
                    raise ImportRunActivationError(f"Import run '{run_id}' not found in report '{r_id}'.")

                conn.execute("UPDATE laboratory_import_runs SET active = FALSE WHERE report_id = ?", [r_id])
                conn.execute("UPDATE laboratory_import_runs SET active = TRUE WHERE report_id = ? AND import_run_id = ?", [r_id, run_id])

                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def delete_report(self, report_id: str, deletion_mode: DeletionMode) -> DeletionResult:
        r_id = report_id.strip()

        with self._lock:
            conn = self._ensure_open()
            conn.execute("BEGIN TRANSACTION")
            try:
                report_row = conn.execute(
                    "SELECT report_id, source_document_hash FROM laboratory_reports WHERE report_id = ?",
                    [r_id],
                ).fetchone()

                if not report_row:
                    raise ReportNotFoundError(f"Report '{r_id}' not found for deletion.")

                doc_hash = report_row[1]

                obs_count = conn.execute("SELECT COUNT(*) FROM laboratory_observations WHERE report_id = ?", [r_id]).fetchone()[0]
                runs_count = conn.execute("SELECT COUNT(*) FROM laboratory_import_runs WHERE report_id = ?", [r_id]).fetchone()[0]

                conn.execute("DELETE FROM laboratory_observations WHERE report_id = ?", [r_id])
                conn.execute("DELETE FROM laboratory_import_runs WHERE report_id = ?", [r_id])
                conn.execute("DELETE FROM laboratory_reports WHERE report_id = ?", [r_id])

                now_utc = datetime.now(timezone.utc)
                tombstone_retained = False

                if deletion_mode == DeletionMode.DELETE_DATA_KEEP_TOMBSTONE:
                    t_id = f"tombstone-{r_id}"
                    conn.execute(
                        """
                        INSERT INTO laboratory_tombstones (tombstone_id, source_document_hash, deleted_at)
                        VALUES (?, ?, ?)
                        """,
                        [t_id, doc_hash, to_naive_utc(now_utc)],
                    )
                    tombstone_retained = True
                elif deletion_mode == DeletionMode.DELETE_EVERYTHING:
                    conn.execute("DELETE FROM laboratory_tombstones WHERE source_document_hash = ?", [doc_hash])

                conn.execute("COMMIT")

                return DeletionResult(
                    report_id=r_id,
                    deleted_reports_count=1,
                    deleted_import_runs_count=runs_count,
                    deleted_observations_count=obs_count,
                    deleted_derived_items_count=1,
                    tombstone_retained=tombstone_retained,
                    deleted_at=now_utc,
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def rebuild_derived_state(self, report_id: str) -> None:
        pass

    def _row_to_report(self, row: tuple) -> LaboratoryReport:
        return LaboratoryReport(
            report_id=row[0],
            collected_at=from_naive_utc(row[1]),
            reported_at=from_naive_utc(row[2]),
            laboratory_name=row[3],
            source_type=row[4],
            source_document_hash=row[5],
            created_at=from_naive_utc(row[6]),
        )

    def _row_to_import_run(self, row: tuple, observations: Tuple[LaboratoryObservation, ...]) -> LaboratoryImportRun:
        warnings_list = tuple(json.loads(row[10])) if row[10] else ()
        return LaboratoryImportRun(
            import_run_id=row[0],
            report_id=row[1],
            parser_version=row[2],
            extractor_version=row[3],
            registry_version=row[4],
            unit_rules_version=row[5],
            started_at=from_naive_utc(row[6]),
            completed_at=from_naive_utc(row[7]),
            status=ImportRunStatus(row[8]),
            active=bool(row[9]),
            warnings=warnings_list,
            observations=observations,
        )

    def _row_to_observation(self, row: tuple) -> LaboratoryObservation:
        ref_range = None
        ref_low, ref_high, ref_text, ref_unit, ref_lab_provided = row[21], row[22], row[23], row[24], row[25]
        if ref_low is not None or ref_high is not None or ref_text is not None:
            ref_range = LaboratoryReferenceRange(
                low=ref_low,
                high=ref_high,
                text=ref_text,
                unit=ref_unit,
                laboratory_provided=bool(ref_lab_provided) if ref_lab_provided is not None else True,
            )

        meta_dict = json.loads(row[44]) if row[44] else {}

        return LaboratoryObservation(
            observation_id=row[0],
            import_run_id=row[1],
            report_id=row[2],
            report_row_index=row[3],
            observation_source_fingerprint=row[4],
            raw_name=row[5],
            raw_value=row[6],
            raw_unit=row[7],
            canonical_code=row[8],
            normalization_status=NormalizationStatus(row[9]),
            requires_review=bool(row[10]),
            alias_match_confidence=row[11],
            value_type=BiomarkerValueType(row[12]),
            numeric_value=row[13],
            text_value=row[14],
            qualitative_value=row[15],
            inequality_operator=row[16],
            range_low=row[17],
            range_high=row[18],
            normalized_value=row[19],
            normalized_unit=row[20],
            laboratory_reference_range=ref_range,
            laboratory_flag=row[26],
            laboratory_provided_critical_flag=row[27],
            collected_at=from_naive_utc(row[28]),
            reported_at=from_naive_utc(row[29]),
            laboratory_name=row[30],
            source_type=row[31],
            source_document_hash=row[32],
            name_confidence=row[33],
            value_confidence=row[34],
            unit_confidence=row[35],
            reference_confidence=row[36],
            extraction_confidence=row[37],
            overall_confidence=row[38],
            verification_status=VerificationStatus(row[39]),
            trend_status=row[40],
            training_context_signal=row[41],
            platform_message_level=PlatformMessageLevel(row[42]),
            is_possible_duplicate=bool(row[43]),
            metadata=meta_dict,
        )
