"""
Comprehensive unit and domain tests for Sprint 5A & 5B: Biomarkers Read Model, Serialization Contract & Edge Cases.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest

from biomarkers import (
    BiomarkerCategory,
    BiomarkersDashboardBuilder,
    BiomarkersDashboardSerializer,
    BiomarkersDashboardStatus,
    ImportRunStatus,
    InMemoryLaboratoryRepository,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReport,
    NormalizationStatus,
    VerificationStatus,
    create_default_biomarker_registry,
    create_default_unit_normalizer,
    create_laboratory_observation,
    parse_laboratory_value,
)


class TestEmptyState:
    def test_empty_repository_yields_unavailable_status(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)

        builder = BiomarkersDashboardBuilder(
            repository=repository,
            biomarker_registry=registry,
            clock=lambda: now,
        )
        dashboard = builder.build()

        assert dashboard.contract_version == "1.0"
        assert dashboard.metadata.status == BiomarkersDashboardStatus.UNAVAILABLE
        assert dashboard.total_reports == 0
        assert dashboard.active_reports == 0
        assert dashboard.total_observations == 0
        assert dashboard.categories == ()
        assert dashboard.unresolved_items == ()

        payload = BiomarkersDashboardSerializer.serialize(dashboard)
        assert payload["contract_version"] == "1.0"
        assert payload["metadata"]["status"] == "unavailable"
        assert payload["summary"]["total_reports"] == 0


class TestActiveRunsAndLatestSelection:
    def test_only_active_run_observations_included_in_dashboard(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        d2 = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(
            report_id="rep-100",
            collected_at=d1,
            source_type="pdf_text",
            source_document_hash="hash100",
        )

        match_glu = registry.match_alias("Glukoza")

        # Inactive Old Run (v1.0) with glucose = 120.0
        parsed1 = parse_laboratory_value("120")
        unit1 = normalizer.convert("glucose", 120.0, "mg/dL")
        obs1 = create_laboratory_observation(
            observation_id="obs-run1",
            report_id="rep-100",
            import_run_id="run-v1",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="120",
            raw_unit="mg/dL",
            source_document_hash="hash100",
            collected_at=d1,
            parsed_value=parsed1,
            biomarker_match=match_glu,
            unit_result=unit1,
        )
        run1 = LaboratoryImportRun(
            import_run_id="run-v1",
            report_id="rep-100",
            parser_version="1.0",
            extractor_version="1.0",
            registry_version="1.0",
            unit_rules_version="1.0",
            started_at=d1,
            completed_at=d1,
            status=ImportRunStatus.COMPLETED,
            active=False,  # Inactive!
            observations=(obs1,),
        )

        # Active Run (v2.0) with glucose = 90.0
        parsed2 = parse_laboratory_value("90")
        unit2 = normalizer.convert("glucose", 90.0, "mg/dL")
        obs2 = create_laboratory_observation(
            observation_id="obs-run2",
            report_id="rep-100",
            import_run_id="run-v2",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hash100",
            collected_at=d2,
            parsed_value=parsed2,
            biomarker_match=match_glu,
            unit_result=unit2,
        )
        run2 = LaboratoryImportRun(
            import_run_id="run-v2",
            report_id="rep-100",
            parser_version="2.0",
            extractor_version="2.0",
            registry_version="2.0",
            unit_rules_version="2.0",
            started_at=d2,
            completed_at=d2,
            status=ImportRunStatus.COMPLETED,
            active=True,  # Active!
            observations=(obs2,),
        )

        repository.save_report_with_import_run(report, run1)
        repository.save_report_with_import_run(report, run2)
        repository.activate_import_run("rep-100", "run-v2")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        assert dashboard.total_observations == 1
        b_summary = dashboard.categories[0].biomarkers[0]
        assert b_summary.latest_observation_id == "obs-run2"
        assert b_summary.latest_value == round(90.0 * 0.05551, 6)

    def test_rejected_observation_is_excluded_from_latest_selection(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        d2 = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-200", collected_at=d1, source_type="pdf_text", source_document_hash="hash200")
        match_fer = registry.match_alias("Ferrytyna")

        # Older valid observation
        obs1 = create_laboratory_observation(
            observation_id="obs-valid",
            report_id="rep-200",
            import_run_id="run-200",
            report_row_index=0,
            raw_name="Ferrytyna",
            raw_value="35",
            raw_unit="µg/L",
            source_document_hash="hash200",
            collected_at=d1,
            parsed_value=parse_laboratory_value("35"),
            biomarker_match=match_fer,
            unit_result=normalizer.convert("ferritin", 35.0, "µg/L"),
        )
        obs1 = LaboratoryObservation(
            observation_id=obs1.observation_id,
            report_id=obs1.report_id,
            import_run_id=obs1.import_run_id,
            report_row_index=obs1.report_row_index,
            observation_source_fingerprint=obs1.observation_source_fingerprint,
            raw_name=obs1.raw_name,
            raw_value=obs1.raw_value,
            raw_unit=obs1.raw_unit,
            canonical_code=obs1.canonical_code,
            normalization_status=obs1.normalization_status,
            numeric_value=obs1.numeric_value,
            normalized_value=obs1.normalized_value,
            normalized_unit=obs1.normalized_unit,
            collected_at=d1,
            verification_status=VerificationStatus.VERIFIED,
        )

        # Newer REJECTED observation
        obs2 = LaboratoryObservation(
            observation_id="obs-rejected",
            report_id="rep-200",
            import_run_id="run-200",
            report_row_index=1,
            observation_source_fingerprint="fingerprint2",
            raw_name="Ferrytyna",
            raw_value="999",
            raw_unit="µg/L",
            canonical_code="ferritin",
            normalization_status=NormalizationStatus.RESOLVED,
            numeric_value=999.0,
            normalized_value=999.0,
            normalized_unit="µg/L",
            collected_at=d2,
            verification_status=VerificationStatus.REJECTED,
        )

        run = LaboratoryImportRun(
            import_run_id="run-200",
            report_id="rep-200",
            parser_version="1.0",
            extractor_version="1.0",
            registry_version="1.0",
            unit_rules_version="1.0",
            started_at=d1,
            completed_at=d1,
            status=ImportRunStatus.COMPLETED,
            active=True,
            observations=(obs1, obs2),
        )

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-200", "run-200")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        iron_cat = next(c for c in dashboard.categories if c.category == BiomarkerCategory.IRON_PANEL)
        b_summary = iron_cat.biomarkers[0]

        assert b_summary.latest_observation_id == "obs-valid"
        assert b_summary.latest_value == 35.0

    def test_tie_break_latest_selection_by_observation_id(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-tie", collected_at=d1, source_type="pdf_text", source_document_hash="hashtie")
        match_glu = registry.match_alias("Glukoza")

        obs_a = create_laboratory_observation(
            observation_id="obs-aaa",
            report_id="rep-tie",
            import_run_id="run-tie",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hashtie",
            collected_at=d1,
            parsed_value=parse_laboratory_value("90"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 90.0, "mg/dL"),
        )
        obs_z = create_laboratory_observation(
            observation_id="obs-zzz",
            report_id="rep-tie",
            import_run_id="run-tie",
            report_row_index=1,
            raw_name="Glukoza",
            raw_value="95",
            raw_unit="mg/dL",
            source_document_hash="hashtie",
            collected_at=d1,  # Same collected_at timestamp!
            parsed_value=parse_laboratory_value("95"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 95.0, "mg/dL"),
        )

        run = LaboratoryImportRun(import_run_id="run-tie", report_id="rep-tie", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs_a, obs_z))

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-tie", "run-tie")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        b_summary = dashboard.categories[0].biomarkers[0]
        # Deterministic tie-breaker selects obs-zzz
        assert b_summary.latest_observation_id == "obs-zzz"


class TestUnresolvedItems:
    def test_unresolved_observation_goes_to_unresolved_items_without_raw_value(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-300", collected_at=d1, source_type="pdf_text", source_document_hash="hash300")
        match_unresolved = registry.match_alias("Nierozpoznane Badanie Badacz")

        obs_unresolved = create_laboratory_observation(
            observation_id="obs-unres",
            report_id="rep-300",
            import_run_id="run-300",
            report_row_index=0,
            raw_name="Nierozpoznane Badanie Badacz",
            raw_value="100.5",  # Secret raw value
            raw_unit="U/L",
            source_document_hash="hash300",
            collected_at=d1,
            parsed_value=parse_laboratory_value("100.5"),
            biomarker_match=match_unresolved,
        )

        run = LaboratoryImportRun(
            import_run_id="run-300",
            report_id="rep-300",
            parser_version="1.0",
            extractor_version="1.0",
            registry_version="1.0",
            unit_rules_version="1.0",
            started_at=d1,
            completed_at=d1,
            status=ImportRunStatus.COMPLETED,
            active=True,
            observations=(obs_unresolved,),
        )

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-300", "run-300")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        assert len(dashboard.unresolved_items) == 1
        item = dashboard.unresolved_items[0]
        assert item.observation_id == "obs-unres"
        assert item.raw_name == "Nierozpoznane Badanie Badacz"

        payload = BiomarkersDashboardSerializer.serialize(dashboard)
        u_payload = payload["unresolved_items"][0]
        assert "raw_value" not in u_payload
        assert u_payload["raw_name"] == "Nierozpoznane Badanie Badacz"


class TestTrendsAndStatusPolicy:
    def test_trend_calculation_for_two_compatible_observations(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        d2 = datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)

        report1 = LaboratoryReport(report_id="rep-401", collected_at=d1, source_type="pdf_text", source_document_hash="hash401")
        report2 = LaboratoryReport(report_id="rep-402", collected_at=d2, source_type="pdf_text", source_document_hash="hash402")

        match_fer = registry.match_alias("Ferrytyna")

        obs1 = create_laboratory_observation(
            observation_id="obs-fer-1",
            report_id="rep-401",
            import_run_id="run-401",
            report_row_index=0,
            raw_name="Ferrytyna",
            raw_value="30",
            raw_unit="µg/L",
            source_document_hash="hash401",
            collected_at=d1,
            parsed_value=parse_laboratory_value("30"),
            biomarker_match=match_fer,
            unit_result=normalizer.convert("ferritin", 30.0, "µg/L"),
        )
        obs2 = create_laboratory_observation(
            observation_id="obs-fer-2",
            report_id="rep-402",
            import_run_id="run-402",
            report_row_index=0,
            raw_name="Ferrytyna",
            raw_value="45",
            raw_unit="µg/L",
            source_document_hash="hash402",
            collected_at=d2,
            parsed_value=parse_laboratory_value("45"),
            biomarker_match=match_fer,
            unit_result=normalizer.convert("ferritin", 45.0, "µg/L"),
        )

        run1 = LaboratoryImportRun(import_run_id="run-401", report_id="rep-401", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs1,))
        run2 = LaboratoryImportRun(import_run_id="run-402", report_id="rep-402", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d2, completed_at=d2, status=ImportRunStatus.COMPLETED, active=True, observations=(obs2,))

        repository.save_report_with_import_run(report1, run1)
        repository.activate_import_run("rep-401", "run-401")
        repository.save_report_with_import_run(report2, run2)
        repository.activate_import_run("rep-402", "run-402")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        iron_cat = next(c for c in dashboard.categories if c.category == BiomarkerCategory.IRON_PANEL)
        fer_summary = iron_cat.biomarkers[0]

        assert fer_summary.trend_available is True
        assert fer_summary.trend_direction == "increasing"
        assert fer_summary.observation_count == 2

    def test_single_observation_yields_unavailable_trend(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-single", collected_at=d1, source_type="pdf_text", source_document_hash="hashsingle")
        match_glu = registry.match_alias("Glukoza")

        obs = create_laboratory_observation(
            observation_id="obs-single",
            report_id="rep-single",
            import_run_id="run-single",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hashsingle",
            collected_at=d1,
            parsed_value=parse_laboratory_value("90"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 90.0, "mg/dL"),
        )
        run = LaboratoryImportRun(import_run_id="run-single", report_id="rep-single", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs,))

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-single", "run-single")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        b_summary = dashboard.categories[0].biomarkers[0]
        assert b_summary.trend_available is False
        assert b_summary.trend_direction == "unavailable"

    def test_incompatible_units_block_trend_calculation(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
        d2 = datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)

        report1 = LaboratoryReport(report_id="rep-u1", collected_at=d1, source_type="pdf_text", source_document_hash="hashu1")
        report2 = LaboratoryReport(report_id="rep-u2", collected_at=d2, source_type="pdf_text", source_document_hash="hashu2")

        match_fer = registry.match_alias("Ferrytyna")

        # Two observations with different un-normalized units
        obs1 = create_laboratory_observation(
            observation_id="obs-incompat-1",
            report_id="rep-u1",
            import_run_id="run-u1",
            report_row_index=0,
            raw_name="Ferrytyna",
            raw_value="30",
            raw_unit="unit_a",
            source_document_hash="hashu1",
            collected_at=d1,
            parsed_value=parse_laboratory_value("30"),
            biomarker_match=match_fer,
        )
        obs2 = create_laboratory_observation(
            observation_id="obs-incompat-2",
            report_id="rep-u2",
            import_run_id="run-u2",
            report_row_index=0,
            raw_name="Ferrytyna",
            raw_value="45",
            raw_unit="unit_b",
            source_document_hash="hashu2",
            collected_at=d2,
            parsed_value=parse_laboratory_value("45"),
            biomarker_match=match_fer,
        )

        run1 = LaboratoryImportRun(import_run_id="run-u1", report_id="rep-u1", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs1,))
        run2 = LaboratoryImportRun(import_run_id="run-u2", report_id="rep-u2", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d2, completed_at=d2, status=ImportRunStatus.COMPLETED, active=True, observations=(obs2,))

        repository.save_report_with_import_run(report1, run1)
        repository.activate_import_run("rep-u1", "run-u1")
        repository.save_report_with_import_run(report2, run2)
        repository.activate_import_run("rep-u2", "run-u2")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        iron_cat = next(c for c in dashboard.categories if c.category == BiomarkerCategory.IRON_PANEL)
        fer_summary = iron_cat.biomarkers[0]
        assert fer_summary.trend_available is False
        assert fer_summary.trend_direction == "unavailable"

    def test_dashboard_status_ready_for_clean_verified_data(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-ready", collected_at=d1, source_type="pdf_text", source_document_hash="hashready")
        match_glu = registry.match_alias("Glukoza")

        obs_verified = create_laboratory_observation(
            observation_id="obs-ver",
            report_id="rep-ready",
            import_run_id="run-ready",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hashready",
            collected_at=d1,
            parsed_value=parse_laboratory_value("90"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 90.0, "mg/dL"),
        )
        # Mark as VERIFIED
        obs_verified = LaboratoryObservation(
            observation_id=obs_verified.observation_id,
            report_id=obs_verified.report_id,
            import_run_id=obs_verified.import_run_id,
            report_row_index=obs_verified.report_row_index,
            observation_source_fingerprint=obs_verified.observation_source_fingerprint,
            raw_name=obs_verified.raw_name,
            raw_value=obs_verified.raw_value,
            raw_unit=obs_verified.raw_unit,
            canonical_code=obs_verified.canonical_code,
            normalization_status=obs_verified.normalization_status,
            numeric_value=obs_verified.numeric_value,
            normalized_value=obs_verified.normalized_value,
            normalized_unit=obs_verified.normalized_unit,
            collected_at=d1,
            verification_status=VerificationStatus.VERIFIED,
            is_possible_duplicate=False,
        )

        run = LaboratoryImportRun(import_run_id="run-ready", report_id="rep-ready", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs_verified,))

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-ready", "run-ready")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        assert dashboard.metadata.status == BiomarkersDashboardStatus.READY
        assert dashboard.metadata.completeness_score == 1.0


class TestSerializationAndPrivacyContract:
    def test_json_native_serialization_conforms_to_contract_v1_0(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-600", collected_at=d1, source_type="pdf_text", source_document_hash="hash600_secret")
        match_glu = registry.match_alias("Glukoza")

        obs = create_laboratory_observation(
            observation_id="obs-600",
            report_id="rep-600",
            import_run_id="run-600",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hash600_secret",
            collected_at=d1,
            parsed_value=parse_laboratory_value("90"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 90.0, "mg/dL"),
            laboratory_flag="H",
        )

        run = LaboratoryImportRun(import_run_id="run-600", report_id="rep-600", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs,))

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-600", "run-600")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        payload = BiomarkersDashboardSerializer.serialize(dashboard)

        # JSON dump smoke test to ensure no non-serializable objects or NaN
        json_str = json.dumps(payload)
        assert json_str is not None

        assert payload["contract_version"] == "1.0"
        assert payload["as_of"] == now.isoformat()
        assert "metadata" in payload
        assert "summary" in payload
        assert "categories" in payload
        assert "unresolved_items" in payload
        assert "data_quality" in payload

        # PRIVACY ASSERTIONS:
        # source_document_hash and filename must NOT be leaked in public payload
        assert "hash600_secret" not in json_str
        assert "source_document_hash" not in json_str
        assert "original_filename" not in json_str
        # laboratory_flag is presented strictly as raw source string
        b_payload = payload["categories"][0]["biomarkers"][0]
        assert b_payload["laboratory_flag"] == "H"
