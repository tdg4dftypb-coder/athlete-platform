"""
Comprehensive Test Suite for Biomarker History Read Model and Builder Engine (Sprint 7D.1).
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from biomarkers.history import BiomarkerHistory, BiomarkerHistoryBuilder, BiomarkerMeasurement
from biomarkers.models import (
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReport,
    NormalizationStatus,
    VerificationStatus,
    create_laboratory_observation,
)
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.registry import BiomarkerMatch, create_default_biomarker_registry
from biomarkers.repository import InMemoryLaboratoryRepository
from biomarkers.units import create_default_unit_normalizer
from biomarkers.values import parse_laboratory_value


def build_sample_observation(
    obs_id: str,
    report_id: str,
    run_id: str,
    row_idx: int,
    canonical_code: str,
    collected_at: datetime,
    raw_name: str,
    raw_value: str,
    raw_unit: str,
    norm_val: float,
    flag: str = None,
) -> LaboratoryObservation:
    registry = create_default_biomarker_registry()
    normalizer = create_default_unit_normalizer()
    definition = registry.get(canonical_code)

    match = BiomarkerMatch(
        canonical_code=canonical_code,
        definition=definition,
        normalization_status=NormalizationStatus.RESOLVED,
        alias_match_confidence=1.0,
        matched_alias=raw_name,
        requires_review=False,
    )
    parsed_val = parse_laboratory_value(raw_value)
    unit_res = normalizer.convert(canonical_code, norm_val, raw_unit) if norm_val is not None else None

    return create_laboratory_observation(
        observation_id=obs_id,
        report_id=report_id,
        import_run_id=run_id,
        report_row_index=row_idx,
        raw_name=raw_name,
        raw_value=raw_value,
        raw_unit=raw_unit,
        source_document_hash=f"hash-{report_id}",
        collected_at=collected_at,
        parsed_value=parsed_val,
        biomarker_match=match,
        unit_result=unit_res,
        laboratory_flag=flag,
    )


def test_biomarker_history_ordering_oldest_to_newest() -> None:
    repo = InMemoryLaboratoryRepository()
    registry = create_default_biomarker_registry()

    dt_2024 = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
    dt_2025 = datetime(2025, 6, 20, 8, 30, tzinfo=timezone.utc)
    dt_2026 = datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)

    # Save out of order reports
    rep_2026 = LaboratoryReport(report_id="rep-2026", collected_at=dt_2026, source_type="pdf_digital", source_document_hash="hash-2026")
    obs_2026 = build_sample_observation("obs-2026", "rep-2026", "run-2026", 1, "hemoglobin", dt_2026, "Hemoglobina", "15.2", "g/dL", 15.2)
    run_2026 = LaboratoryImportRun("run-2026", "rep-2026", "1.0", "1.0", "1.0", "1.0", dt_2026, dt_2026, ImportRunStatus.COMPLETED, True, (), (obs_2026,))
    repo.save_report_with_import_run(rep_2026, run_2026)

    rep_2024 = LaboratoryReport(report_id="rep-2024", collected_at=dt_2024, source_type="pdf_digital", source_document_hash="hash-2024")
    obs_2024 = build_sample_observation("obs-2024", "rep-2024", "run-2024", 1, "hemoglobin", dt_2024, "Hemoglobina", "14.0", "g/dL", 14.0)
    run_2024 = LaboratoryImportRun("run-2024", "rep-2024", "1.0", "1.0", "1.0", "1.0", dt_2024, dt_2024, ImportRunStatus.COMPLETED, True, (), (obs_2024,))
    repo.save_report_with_import_run(rep_2024, run_2024)

    rep_2025 = LaboratoryReport(report_id="rep-2025", collected_at=dt_2025, source_type="pdf_digital", source_document_hash="hash-2025")
    obs_2025 = build_sample_observation("obs-2025", "rep-2025", "run-2025", 1, "hemoglobin", dt_2025, "Hemoglobina", "14.8", "g/dL", 14.8)
    run_2025 = LaboratoryImportRun("run-2025", "rep-2025", "1.0", "1.0", "1.0", "1.0", dt_2025, dt_2025, ImportRunStatus.COMPLETED, True, (), (obs_2025,))
    repo.save_report_with_import_run(rep_2025, run_2025)

    builder = BiomarkerHistoryBuilder(repository=repo, biomarker_registry=registry)
    history = builder.build_for_code("hemoglobin")

    assert history.canonical_code == "hemoglobin"
    assert history.display_name == "Hemoglobina"
    assert history.preferred_unit == "g/dL"
    assert len(history.measurements) == 3

    # Assert strict chronological ordering: oldest -> newest
    assert history.measurements[0].collected_at == dt_2024
    assert history.measurements[0].numeric_value == 140.0

    assert history.measurements[1].collected_at == dt_2025
    assert history.measurements[1].numeric_value == 148.0

    assert history.measurements[2].collected_at == dt_2026
    assert history.measurements[2].numeric_value == 152.0


def test_biomarker_history_duplicate_timestamps_and_deduplication() -> None:
    repo = InMemoryLaboratoryRepository()
    registry = create_default_biomarker_registry()

    dt = datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc)

    rep1 = LaboratoryReport(report_id="rep-1", collected_at=dt, source_type="pdf_digital", source_document_hash="hash-1")
    obs1 = build_sample_observation("obs-1", "rep-1", "run-1", 1, "ferritin", dt, "Ferrytyna", "120", "ng/mL", 120.0)
    run1 = LaboratoryImportRun("run-1", "rep-1", "1.0", "1.0", "1.0", "1.0", dt, dt, ImportRunStatus.COMPLETED, True, (), (obs1,))
    repo.save_report_with_import_run(rep1, run1)

    # Save exact duplicate observation (e.g. duplicate report or re-imported run)
    rep2 = LaboratoryReport(report_id="rep-2", collected_at=dt, source_type="pdf_digital", source_document_hash="hash-2")
    obs2 = build_sample_observation("obs-2", "rep-2", "run-2", 1, "ferritin", dt, "Ferrytyna", "120", "ng/mL", 120.0)
    run2 = LaboratoryImportRun("run-2", "rep-2", "1.0", "1.0", "1.0", "1.0", dt, dt, ImportRunStatus.COMPLETED, True, (), (obs2,))
    repo.save_report_with_import_run(rep2, run2)

    builder = BiomarkerHistoryBuilder(repository=repo, biomarker_registry=registry)
    history = builder.build_for_code("ferritin")

    # Duplicate observation at identical timestamp is NOT duplicated
    assert len(history.measurements) == 1
    assert history.measurements[0].numeric_value == 120.0


def test_biomarker_history_missing_or_naive_dates() -> None:
    repo = InMemoryLaboratoryRepository()
    registry = create_default_biomarker_registry()

    dt_naive = datetime(2026, 5, 10, 14, 0)  # Naive datetime without tzinfo

    rep = LaboratoryReport(report_id="rep-naive", collected_at=dt_naive.replace(tzinfo=timezone.utc), source_type="pdf_digital", source_document_hash="hash-naive")
    obs = build_sample_observation("obs-naive", "rep-naive", "run-naive", 1, "glucose", dt_naive, "Glukoza", "95", "mg/dL", 95.0)
    run = LaboratoryImportRun("run-naive", "rep-naive", "1.0", "1.0", "1.0", "1.0", datetime.now(timezone.utc), datetime.now(timezone.utc), ImportRunStatus.COMPLETED, True, (), (obs,))
    repo.save_report_with_import_run(rep, run)

    builder = BiomarkerHistoryBuilder(repository=repo, biomarker_registry=registry)
    history = builder.build_for_code("glucose")

    assert len(history.measurements) == 1
    m = history.measurements[0]
    assert m.collected_at.tzinfo is not None
    assert m.collected_at == datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc)


def test_biomarker_history_mixed_qualitative_and_numeric_values() -> None:
    repo = InMemoryLaboratoryRepository()
    registry = create_default_biomarker_registry()

    dt_num = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
    dt_qual = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)

    # 1. Numeric HBsAg
    rep1 = LaboratoryReport(report_id="rep-hbs-1", collected_at=dt_num, source_type="pdf_digital", source_document_hash="hash-hbs-1")
    obs1 = build_sample_observation("obs-hbs-1", "rep-hbs-1", "run-hbs-1", 1, "hbs_antigen_numeric", dt_num, "HBs-antygen (V39)", "0.37", "S/CO", 0.37)
    run1 = LaboratoryImportRun("run-hbs-1", "rep-hbs-1", "1.0", "1.0", "1.0", "1.0", dt_num, dt_num, ImportRunStatus.COMPLETED, True, (), (obs1,))
    repo.save_report_with_import_run(rep1, run1)

    # 2. Qualitative HBsAg
    rep2 = LaboratoryReport(report_id="rep-hbs-2", collected_at=dt_qual, source_type="pdf_digital", source_document_hash="hash-hbs-2")
    obs2 = build_sample_observation("obs-hbs-2", "rep-hbs-2", "run-hbs-2", 1, "hbs_antigen_qualitative", dt_qual, "HBs-antygen", "nieobecny", "", None)
    run2 = LaboratoryImportRun("run-hbs-2", "rep-hbs-2", "1.0", "1.0", "1.0", "1.0", dt_qual, dt_qual, ImportRunStatus.COMPLETED, True, (), (obs2,))
    repo.save_report_with_import_run(rep2, run2)

    builder = BiomarkerHistoryBuilder(repository=repo, biomarker_registry=registry)
    hist_num = builder.build_for_code("hbs_antigen_numeric")
    hist_qual = builder.build_for_code("hbs_antigen_qualitative")

    assert len(hist_num.measurements) == 1
    assert hist_num.measurements[0].numeric_value == 0.37

    assert len(hist_qual.measurements) == 1
    assert hist_qual.measurements[0].numeric_value is None
    assert hist_qual.measurements[0].qualitative_value in ("NEGATIVE", "nieobecny")


def test_biomarker_history_builder_all_and_duckdb_integration(tmp_path: Path) -> None:
    db_file = str(tmp_path / "history_duckdb.duckdb")
    repo = DuckDBLaboratoryRepository(db_path=db_file)
    registry = create_default_biomarker_registry()

    dt_1 = datetime(2025, 2, 1, 8, 0, tzinfo=timezone.utc)
    dt_2 = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)

    rep1 = LaboratoryReport(report_id="rep-d1", collected_at=dt_1, source_type="pdf_digital", source_document_hash="hash-d1")
    obs1 = build_sample_observation("obs-d1", "rep-d1", "run-d1", 1, "leukocytes", dt_1, "Leukocyty", "5.5", "10^3/µL", 5.5)
    run1 = LaboratoryImportRun("run-d1", "rep-d1", "1.0", "1.0", "1.0", "1.0", dt_1, dt_1, ImportRunStatus.COMPLETED, True, (), (obs1,))
    repo.save_report_with_import_run(rep1, run1)

    rep2 = LaboratoryReport(report_id="rep-d2", collected_at=dt_2, source_type="pdf_digital", source_document_hash="hash-d2")
    obs2 = build_sample_observation("obs-d2", "rep-d2", "run-d2", 1, "leukocytes", dt_2, "Leukocyty", "6.2", "10^3/µL", 6.2)
    run2 = LaboratoryImportRun("run-d2", "rep-d2", "1.0", "1.0", "1.0", "1.0", dt_2, dt_2, ImportRunStatus.COMPLETED, True, (), (obs2,))
    repo.save_report_with_import_run(rep2, run2)

    builder = BiomarkerHistoryBuilder(repository=repo, biomarker_registry=registry)
    histories = builder.build_all()

    assert "leukocytes" in histories
    wbc_history = histories["leukocytes"]
    assert wbc_history.display_name == "Leukocyty"
    assert len(wbc_history.measurements) == 2
    assert wbc_history.measurements[0].collected_at == dt_1
    assert wbc_history.measurements[0].numeric_value == 5.5
    assert wbc_history.measurements[1].collected_at == dt_2
    assert wbc_history.measurements[1].numeric_value == 6.2

    repo.close()
