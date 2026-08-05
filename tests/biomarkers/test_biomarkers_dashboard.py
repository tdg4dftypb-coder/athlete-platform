"""
Comprehensive unit and domain tests for Sprint 5A: Biomarkers Read Model and Serialization Contract.
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
        assert b_summary.numeric_value if hasattr(b_summary, "numeric_value") else b_summary.latest_value == round(90.0 * 0.05551, 6)

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
        # Manually update verification_status to VERIFIED
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
        assert not hasattr(item, "raw_value")  # Confirm no raw_value field in item model

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

    def test_dashboard_status_partial_when_unverified_or_unresolved_exists(self):
        repository = InMemoryLaboratoryRepository()
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        d1 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)

        report = LaboratoryReport(report_id="rep-500", collected_at=d1, source_type="pdf_text", source_document_hash="hash500")
        match_glu = registry.match_alias("Glukoza")

        obs_unverified = create_laboratory_observation(
            observation_id="obs-unver",
            report_id="rep-500",
            import_run_id="run-500",
            report_row_index=0,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            source_document_hash="hash500",
            collected_at=d1,
            parsed_value=parse_laboratory_value("90"),
            biomarker_match=match_glu,
            unit_result=normalizer.convert("glucose", 90.0, "mg/dL"),
        )
        # Unverified by default!

        run = LaboratoryImportRun(import_run_id="run-500", report_id="rep-500", parser_version="1.0", extractor_version="1.0", registry_version="1.0", unit_rules_version="1.0", started_at=d1, completed_at=d1, status=ImportRunStatus.COMPLETED, active=True, observations=(obs_unverified,))

        repository.save_report_with_import_run(report, run)
        repository.activate_import_run("rep-500", "run-500")

        builder = BiomarkersDashboardBuilder(repository=repository, biomarker_registry=registry, clock=lambda: now)
        dashboard = builder.build()

        assert dashboard.metadata.status == BiomarkersDashboardStatus.PARTIAL
        assert "unverified" in dashboard.categories[0].biomarkers[0].limitations[0]


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
        # source_document_hash must NOT be leaked in public payload
        assert "hash600_secret" not in json_str
        assert "source_document_hash" not in json_str
        # laboratory_flag is presented strictly as raw source string
        b_payload = payload["categories"][0]["biomarkers"][0]
        assert b_payload["laboratory_flag"] == "H"
