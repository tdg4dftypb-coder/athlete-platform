"""
Comprehensive domain and unit tests for Biomarkers & Laboratory Intelligence (Sprint 2).
"""

from datetime import datetime, timezone
import pytest

from biomarkers import (
    BiomarkerCategory,
    BiomarkerDefinition,
    BiomarkerRegistry,
    BiomarkerValueType,
    DuplicateAliasError,
    DuplicateCanonicalCodeError,
    ImportRunStatus,
    InvalidBiomarkerDefinitionError,
    InvalidImportRunError,
    InvalidLaboratoryObservationError,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReferenceRange,
    LaboratoryReport,
    NormalizationStatus,
    PlatformMessageLevel,
    VerificationStatus,
    calculate_observation_fingerprint,
    create_default_biomarker_registry,
)


class TestBiomarkerDefinition:
    def test_valid_definition(self):
        definition = BiomarkerDefinition(
            canonical_code="ferritin",
            canonical_name="Ferrytyna",
            category=BiomarkerCategory.IRON_PANEL,
            default_unit="µg/L",
            accepted_aliases=("Ferrytyna", " Ferritin ", "FER"),
            accepted_units=("µg/L", "ng/mL"),
            value_type=BiomarkerValueType.NUMERIC,
        )
        assert definition.canonical_code == "ferritin"
        assert definition.canonical_name == "Ferrytyna"
        assert len(definition.accepted_aliases) == 3
        assert "Ferrytyna" in definition.accepted_aliases
        assert "Ferritin" in definition.accepted_aliases

    def test_empty_canonical_code_raises_error(self):
        with pytest.raises(InvalidBiomarkerDefinitionError, match="canonical_code cannot be empty"):
            BiomarkerDefinition(
                canonical_code="   ",
                canonical_name="Glukoza",
                category=BiomarkerCategory.OTHER,
                default_unit="mmol/L",
                accepted_aliases=("glu",),
                accepted_units=("mmol/L",),
                value_type=BiomarkerValueType.NUMERIC,
            )

    def test_duplicate_alias_within_definition_raises_error(self):
        with pytest.raises(InvalidBiomarkerDefinitionError, match="Duplicate alias"):
            BiomarkerDefinition(
                canonical_code="glucose",
                canonical_name="Glukoza",
                category=BiomarkerCategory.OTHER,
                default_unit="mmol/L",
                accepted_aliases=("Glukoza", "glukoza", "GLU"),
                accepted_units=("mmol/L",),
                value_type=BiomarkerValueType.NUMERIC,
            )


class TestBiomarkerRegistry:
    def test_lookup_by_canonical_code(self):
        registry = create_default_biomarker_registry()
        def_glucose = registry.get("glucose")
        assert def_glucose is not None
        assert def_glucose.canonical_name == "Glukoza"

        # Case-insensitive lookup
        def_ferritin = registry.get("  FERRITIN  ")
        assert def_ferritin is not None
        assert def_ferritin.canonical_code == "ferritin"

    def test_match_alias_case_insensitive_and_trimmed(self):
        registry = create_default_biomarker_registry()
        
        match = registry.match_alias("   glukoza na czczo   ")
        assert match.normalization_status == NormalizationStatus.RESOLVED
        assert match.canonical_code == "glucose"
        assert match.alias_match_confidence == 1.0
        assert not match.requires_review
        assert match.definition is not None

    def test_unknown_alias_returns_unresolved_without_unknown_slug(self):
        registry = create_default_biomarker_registry()
        
        match = registry.match_alias("Nietypowe Badanie Laboratoryjne")
        assert match.normalization_status == NormalizationStatus.UNRESOLVED
        assert match.canonical_code is None
        assert match.definition is None
        assert match.alias_match_confidence == 0.0
        assert match.requires_review is True
        # Verify NO unknown_<slug> format generated
        assert match.canonical_code != "unknown_nietypowe_badanie_laboratoryjne"

    def test_duplicate_canonical_code_registration_raises_error(self):
        registry = create_default_biomarker_registry()
        duplicate_def = BiomarkerDefinition(
            canonical_code="glucose",
            canonical_name="Glukoza Zdublowana",
            category=BiomarkerCategory.OTHER,
            default_unit="mmol/L",
            accepted_aliases=("glu2",),
            accepted_units=("mmol/L",),
            value_type=BiomarkerValueType.NUMERIC,
        )
        with pytest.raises(DuplicateCanonicalCodeError):
            registry.register(duplicate_def)

    def test_alias_collision_across_definitions_raises_error(self):
        registry = create_default_biomarker_registry()
        colliding_def = BiomarkerDefinition(
            canonical_code="new_marker",
            canonical_name="Nowy Marker",
            category=BiomarkerCategory.OTHER,
            default_unit="mg/dL",
            accepted_aliases=("ferrytyna", "new_alias"),  # 'ferrytyna' belongs to ferritin
            accepted_units=("mg/dL",),
            value_type=BiomarkerValueType.NUMERIC,
        )
        with pytest.raises(DuplicateAliasError):
            registry.register(colliding_def)

    def test_inactive_definition_behavior(self):
        registry = BiomarkerRegistry()
        inactive_def = BiomarkerDefinition(
            canonical_code="old_marker",
            canonical_name="Stary Marker",
            category=BiomarkerCategory.OTHER,
            default_unit="U/L",
            accepted_aliases=("stary_alias",),
            accepted_units=("U/L",),
            value_type=BiomarkerValueType.NUMERIC,
            active=False,
        )
        registry.register(inactive_def)

        # Inactive definitions should be ignored by default in match and get
        assert registry.get("old_marker") is None
        assert registry.get("old_marker", include_inactive=True) is not None

        match_normal = registry.match_alias("stary_alias")
        assert match_normal.normalization_status == NormalizationStatus.UNRESOLVED

        match_inactive = registry.match_alias("stary_alias", include_inactive=True)
        assert match_inactive.normalization_status == NormalizationStatus.RESOLVED


class TestLaboratoryObservation:
    def test_unresolved_observation_invariants(self):
        # Valid unresolved observation
        obs = LaboratoryObservation(
            observation_id="obs-101",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=1,
            observation_source_fingerprint="abc123hash",
            raw_name="Nierozpoznany Marker",
            raw_value="15.2",
            raw_unit="U/L",
            canonical_code=None,
            normalization_status=NormalizationStatus.UNRESOLVED,
            requires_review=True,
        )
        assert obs.canonical_code is None
        assert obs.normalization_status == NormalizationStatus.UNRESOLVED
        assert obs.requires_review is True

        # Invalid: UNRESOLVED with canonical_code set
        with pytest.raises(InvalidLaboratoryObservationError, match="canonical_code = None"):
            LaboratoryObservation(
                observation_id="obs-102",
                report_id="rep-001",
                import_run_id="run-001",
                report_row_index=2,
                observation_source_fingerprint="abc123hash2",
                raw_name="Nierozpoznany Marker",
                raw_value="15.2",
                raw_unit="U/L",
                canonical_code="glucose",  # Invalid for UNRESOLVED!
                normalization_status=NormalizationStatus.UNRESOLVED,
                requires_review=True,
            )

    def test_resolved_observation_invariants(self):
        obs = LaboratoryObservation(
            observation_id="obs-201",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=1,
            observation_source_fingerprint="fp123",
            raw_name="Glukoza na czczo",
            raw_value="90",
            raw_unit="mg/dL",
            canonical_code="glucose",
            normalization_status=NormalizationStatus.RESOLVED,
            requires_review=False,
            numeric_value=90.0,
        )
        assert obs.canonical_code == "glucose"
        assert obs.normalization_status == NormalizationStatus.RESOLVED
        assert obs.raw_name == "Glukoza na czczo"

        with pytest.raises(InvalidLaboratoryObservationError, match="non-empty canonical_code"):
            LaboratoryObservation(
                observation_id="obs-202",
                report_id="rep-001",
                import_run_id="run-001",
                report_row_index=2,
                observation_source_fingerprint="fp124",
                raw_name="Glukoza",
                raw_value="90",
                raw_unit="mg/dL",
                canonical_code=None,  # Invalid for RESOLVED!
                normalization_status=NormalizationStatus.RESOLVED,
                requires_review=False,
            )

    def test_value_types_representation(self):
        # Bounded inequality: "< 0.01"
        obs_inequality = LaboratoryObservation(
            observation_id="obs-301",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=1,
            observation_source_fingerprint="fp301",
            raw_name="hs-CRP",
            raw_value="< 0.01",
            raw_unit="mg/L",
            value_type=BiomarkerValueType.BOUNDED_INEQUALITY,
            inequality_operator="<",
            numeric_value=0.01,
        )
        assert obs_inequality.inequality_operator == "<"
        assert obs_inequality.numeric_value == 0.01

        # Qualitative: "POSITIVE"
        obs_qualitative = LaboratoryObservation(
            observation_id="obs-302",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=2,
            observation_source_fingerprint="fp302",
            raw_name="Białko w moczu",
            raw_value="Obecne",
            raw_unit="",
            value_type=BiomarkerValueType.QUALITATIVE,
            qualitative_value="POSITIVE",
        )
        assert obs_qualitative.qualitative_value == "POSITIVE"

    def test_confidence_scores_stored_individually(self):
        obs = LaboratoryObservation(
            observation_id="obs-401",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=1,
            observation_source_fingerprint="fp401",
            raw_name="Ferrytyna",
            raw_value="45",
            raw_unit="µg/L",
            name_confidence=1.0,
            value_confidence=0.95,
            unit_confidence=1.0,
            reference_confidence=0.8,
            extraction_confidence=0.9,
            overall_confidence=0.93,
        )
        assert obs.name_confidence == 1.0
        assert obs.value_confidence == 0.95
        assert obs.reference_confidence == 0.8
        assert obs.overall_confidence == 0.93


class TestLaboratoryImportRunAndReport:
    def test_valid_import_run_creation(self):
        now = datetime.now(timezone.utc)
        obs = LaboratoryObservation(
            observation_id="obs-501",
            report_id="rep-001",
            import_run_id="run-001",
            report_row_index=1,
            observation_source_fingerprint="fp501",
            raw_name="TSH",
            raw_value="2.1",
            raw_unit="mIU/L",
        )
        run = LaboratoryImportRun(
            import_run_id="run-001",
            report_id="rep-001",
            parser_version="1.0",
            extractor_version="1.0",
            registry_version="1.0",
            unit_rules_version="1.0",
            started_at=now,
            completed_at=now,
            status=ImportRunStatus.COMPLETED,
            active=True,
            observations=(obs,),
        )
        assert run.status == ImportRunStatus.COMPLETED
        assert len(run.observations) == 1

    def test_completed_import_run_requires_completed_at(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(InvalidImportRunError, match="completed_at is required"):
            LaboratoryImportRun(
                import_run_id="run-002",
                report_id="rep-001",
                parser_version="1.0",
                extractor_version="1.0",
                registry_version="1.0",
                unit_rules_version="1.0",
                started_at=now,
                completed_at=None,  # Invalid for COMPLETED!
                status=ImportRunStatus.COMPLETED,
            )

    def test_import_run_observations_report_id_mismatch_raises_error(self):
        now = datetime.now(timezone.utc)
        mismatched_obs = LaboratoryObservation(
            observation_id="obs-502",
            report_id="rep-OTHER",  # Mismatch!
            import_run_id="run-003",
            report_row_index=1,
            observation_source_fingerprint="fp502",
            raw_name="TSH",
            raw_value="2.1",
            raw_unit="mIU/L",
        )
        with pytest.raises(InvalidImportRunError, match="does not match import run report_id"):
            LaboratoryImportRun(
                import_run_id="run-003",
                report_id="rep-001",
                parser_version="1.0",
                extractor_version="1.0",
                registry_version="1.0",
                unit_rules_version="1.0",
                started_at=now,
                status=ImportRunStatus.IN_PROGRESS,
                observations=(mismatched_obs,),
            )


class TestFingerprint:
    def test_fingerprint_determinism_and_sha256_format(self):
        now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
        fp1 = calculate_observation_fingerprint(
            source_document_hash="hash123",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            collected_at=now,
        )
        fp2 = calculate_observation_fingerprint(
            source_document_hash="hash123",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            collected_at=now,
        )
        assert len(fp1) == 64  # Hex SHA-256
        assert fp1 == fp2

    def test_changing_component_alters_fingerprint(self):
        now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
        base_fp = calculate_observation_fingerprint(
            source_document_hash="hash123",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            collected_at=now,
        )
        # Change row index
        fp_row = calculate_observation_fingerprint(
            source_document_hash="hash123",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=2,  # Changed!
            raw_name="Glukoza",
            raw_value="90",
            raw_unit="mg/dL",
            collected_at=now,
        )
        assert base_fp != fp_row

        # Change raw_name
        fp_name = calculate_observation_fingerprint(
            source_document_hash="hash123",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            raw_name="Hemoglobina",  # Changed!
            raw_value="90",
            raw_unit="mg/dL",
            collected_at=now,
        )
        assert base_fp != fp_name


class TestMedicalSafetyContracts:
    def test_absence_of_urgent_review_level(self):
        levels = [level.value for level in PlatformMessageLevel]
        assert "urgent_review" not in levels
        assert "INFORMATIONAL" in PlatformMessageLevel.__members__
        assert "ATTENTION" in PlatformMessageLevel.__members__
        assert "CONSULT_CLINICIAN" in PlatformMessageLevel.__members__

    def test_no_medical_diagnoses_or_custom_athletic_ranges_in_seed(self):
        registry = create_default_biomarker_registry()
        for definition in registry.list_definitions():
            # Seed definitions must not contain hardcoded medical reference ranges
            assert not hasattr(definition, "reference_low")
            assert not hasattr(definition, "reference_high")
