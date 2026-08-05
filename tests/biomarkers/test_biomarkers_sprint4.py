"""
Comprehensive unit and domain tests for Sprint 4: Ingestion Pipeline, Repository, Reprocessing & Deletion.
"""

from datetime import datetime, timezone
import pytest

from biomarkers import (
    BiomarkerCategory,
    DeletionMode,
    EmptySourceDocumentError,
    ImportRunStatus,
    InMemoryLaboratoryRepository,
    InMemorySourceDocumentStore,
    LaboratoryDeletionError,
    LaboratoryDeletionService,
    LaboratoryIngestionRequest,
    LaboratoryIngestionService,
    LaboratoryObservation,
    NormalizationStatus,
    PlatformMessageLevel,
    RawLaboratoryRow,
    ReportNotFoundError,
    SourceDocumentIdentity,
    SyntheticLaboratoryDocumentExtractor,
    SyntheticLaboratoryResultParser,
    VerificationStatus,
    calculate_source_document_hash,
    create_default_biomarker_registry,
    create_default_unit_normalizer,
)


class TestSourceDocumentIdentity:
    def test_sha256_hash_determinism_and_no_filename_dependency(self):
        content = b"PDF-1.4 synthetic laboratory test file content"
        hash1 = calculate_source_document_hash(content)
        hash2 = calculate_source_document_hash(content)

        assert len(hash1) == 64
        assert hash1 == hash2

    def test_byte_change_alters_hash(self):
        c1 = b"PDF-1.4 test 1"
        c2 = b"PDF-1.4 test 2"
        assert calculate_source_document_hash(c1) != calculate_source_document_hash(c2)

    def test_empty_content_raises_error(self):
        with pytest.raises(EmptySourceDocumentError, match="cannot be empty"):
            calculate_source_document_hash(b"")

    def test_identity_model_validation(self):
        identity = SourceDocumentIdentity(
            source_document_hash="a" * 64,
            byte_length=100,
        )
        assert identity.byte_length == 100


class TestRawLaboratoryRow:
    def test_valid_row_preserves_raw_fields(self):
        row = RawLaboratoryRow(
            report_row_index=0,
            raw_name="   Glukoza na czczo   ",
            raw_value="  90 mg/dL  ",
            raw_unit="mg/dL",
        )
        assert row.report_row_index == 0
        assert row.raw_name == "   Glukoza na czczo   "
        assert row.raw_value == "  90 mg/dL  "

    def test_invalid_row_index_raises_error(self):
        with pytest.raises(ValueError, match="report_row_index must be >= 0"):
            RawLaboratoryRow(report_row_index=-1, raw_name="GLU", raw_value="90")

    def test_empty_name_or_value_raises_error(self):
        with pytest.raises(ValueError, match="raw_name cannot be empty"):
            RawLaboratoryRow(report_row_index=0, raw_name="  ", raw_value="90")


class TestIngestionPipelineAndService:
    def test_successful_synthetic_ingestion_pipeline(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Glukoza | 90 | mg/dL | 70-99\n1 | Ferrytyna | 32 | ng/mL | 30-200"
        req = LaboratoryIngestionRequest(content=content)

        res = service.ingest(req)

        assert res.duplicate_document is False
        assert res.status == ImportRunStatus.COMPLETED
        assert len(res.observations) == 2
        assert res.report is not None

        # Verify glucose conversion (90 mg/dL -> ~4.9959 mmol/L)
        glu_obs = next(o for o in res.observations if o.canonical_code == "glucose")
        assert glu_obs.raw_name == "Glukoza"
        assert glu_obs.raw_value == "90"
        assert glu_obs.numeric_value == 90.0
        assert glu_obs.normalized_value == round(90.0 * 0.05551, 6)
        assert glu_obs.normalized_unit == "mmol/L"
        assert glu_obs.platform_message_level == PlatformMessageLevel.INFORMATIONAL

    def test_unresolved_biomarker_handling_in_ingestion(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Nierozpoznany Marker XYZ | 15.2 | U/L | 0-20"
        req = LaboratoryIngestionRequest(content=content)

        res = service.ingest(req)

        assert res.unresolved_count == 1
        obs = res.observations[0]
        assert obs.canonical_code is None
        assert obs.normalization_status == NormalizationStatus.UNRESOLVED
        assert obs.requires_review is True

    def test_idempotency_duplicate_document_check(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Glukoza | 90 | mg/dL | 70-99"
        req = LaboratoryIngestionRequest(content=content)

        res1 = service.ingest(req)
        assert res1.duplicate_document is False

        # Re-ingest exact same content
        res2 = service.ingest(req)
        assert res2.duplicate_document is True
        assert "SHA-256 duplicate" in res2.warnings[0]
        assert res2.report.report_id == res1.report.report_id


class TestRepositoryAndReprocessing:
    def test_repository_atomic_active_run_invariant(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Glukoza | 90 | mg/dL | 70-99"
        res = service.ingest(LaboratoryIngestionRequest(content=content))

        active_run_before = repository.get_active_import_run(res.report.report_id)
        assert active_run_before.import_run_id == res.import_run.import_run_id
        assert active_run_before.active is True

        # Reprocess report with new version
        reprocess_res = service.reprocess_report(
            report_id=res.report.report_id,
            content=content,
            parser_version="2.0",
        )

        runs = repository.get_import_runs(res.report.report_id)
        assert len(runs) == 2

        active_run_after = repository.get_active_import_run(res.report.report_id)
        assert active_run_after.import_run_id == reprocess_res.import_run.import_run_id
        assert active_run_after.parser_version == "2.0"

        # Verify old run is deactivated
        old_run = next(r for r in runs if r.import_run_id == res.import_run.import_run_id)
        assert old_run.active is False


class TestCrossReportDuplicates:
    def test_possible_duplicate_flagged_across_reports(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        date_fixed = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        # Ingest report 1
        c1 = b"0 | Glukoza | 90 | mg/dL | 70-99"
        res1 = service.ingest(LaboratoryIngestionRequest(content=c1, collected_at_fallback=date_fixed))
        assert res1.possible_duplicate_count == 0

        # Ingest report 2 with different content but matching glucose date & value
        c2 = b"0 | Glukoza | 90 | mg/dL | 70-99\n1 | TSH | 2.1 | mIU/L | 0.4-4.0"
        res2 = service.ingest(LaboratoryIngestionRequest(content=c2, collected_at_fallback=date_fixed))

        assert res2.possible_duplicate_count == 1
        glu_obs = next(o for o in res2.observations if o.canonical_code == "glucose")
        assert glu_obs.is_possible_duplicate is True


class TestDeletionSemantics:
    def test_delete_data_keep_tombstone(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        doc_store = InMemorySourceDocumentStore()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Glukoza | 90 | mg/dL | 70-99"
        doc_hash = calculate_source_document_hash(content)
        doc_store.save(doc_hash, content)

        res = service.ingest(LaboratoryIngestionRequest(content=content))
        report_id = res.report.report_id

        deletion_service = LaboratoryDeletionService(repository=repository, document_store=doc_store)
        del_res = deletion_service.delete(report_id, deletion_mode=DeletionMode.DELETE_DATA_KEEP_TOMBSTONE)

        assert del_res.tombstone_retained is True
        assert repository.get_report(report_id) is None
        assert doc_store.exists(doc_hash) is False

    def test_delete_everything(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        repository = InMemoryLaboratoryRepository()
        doc_store = InMemorySourceDocumentStore()
        extractor = SyntheticLaboratoryDocumentExtractor()
        parser = SyntheticLaboratoryResultParser()

        service = LaboratoryIngestionService(
            extractor=extractor,
            parser=parser,
            biomarker_registry=registry,
            unit_normalizer=normalizer,
            repository=repository,
        )

        content = b"0 | Glukoza | 90 | mg/dL | 70-99"
        res = service.ingest(LaboratoryIngestionRequest(content=content))
        report_id = res.report.report_id

        deletion_service = LaboratoryDeletionService(repository=repository, document_store=doc_store)
        del_res = deletion_service.delete(report_id, deletion_mode=DeletionMode.DELETE_EVERYTHING)

        assert del_res.tombstone_retained is False
        assert repository.get_report(report_id) is None


class TestPrivacySafeErrors:
    def test_exceptions_do_not_leak_raw_health_data(self):
        with pytest.raises(EmptySourceDocumentError) as exc_info:
            calculate_source_document_hash(b"")
        assert "cannot be empty" in str(exc_info.value)
        # Ensure no raw metrics or filenames leaked
        assert "mg/dL" not in str(exc_info.value)
