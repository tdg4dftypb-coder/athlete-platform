"""
Comprehensive unit and domain tests for Sprint 3: Unit Normalizer, Value Parser, Confidence Components.
"""

import math
from datetime import datetime, timezone
import pytest

from biomarkers import (
    BiomarkerCategory,
    BiomarkerValueType,
    ConfidenceAssessment,
    ConfidenceComponents,
    DuplicateUnitConversionRuleError,
    InvalidConfidenceComponentError,
    InvalidLaboratoryValueError,
    InvalidUnitConversionRuleError,
    LaboratoryObservation,
    NormalizationStatus,
    ParsedLaboratoryValue,
    PlatformMessageLevel,
    UnitAliasRegistry,
    UnitConversionRule,
    UnitNormalizationResult,
    UnitNormalizer,
    VerificationStatus,
    create_default_biomarker_registry,
    create_default_unit_normalizer,
    create_laboratory_observation,
    evaluate_confidence_eligibility,
    parse_laboratory_value,
)


class TestUnitConversionRules:
    def test_valid_rule_creation(self):
        rule = UnitConversionRule(
            biomarker_code="glucose",
            source_unit="mg/dL",
            target_unit="mmol/L",
            conversion_factor=0.05551,
        )
        assert rule.biomarker_code == "glucose"
        assert rule.source_unit == "mg/dL"
        assert rule.target_unit == "mmol/L"

    def test_empty_biomarker_code_raises_error(self):
        with pytest.raises(InvalidUnitConversionRuleError, match="biomarker_code cannot be empty"):
            UnitConversionRule(
                biomarker_code="   ",
                source_unit="mg/dL",
                target_unit="mmol/L",
                conversion_factor=0.05551,
            )

    def test_identical_source_and_target_raises_error(self):
        with pytest.raises(InvalidUnitConversionRuleError, match="must be different"):
            UnitConversionRule(
                biomarker_code="glucose",
                source_unit="mmol/L",
                target_unit="mmol/L",
                conversion_factor=1.0,
            )

    def test_non_finite_factor_raises_error(self):
        with pytest.raises(InvalidUnitConversionRuleError, match="finite float"):
            UnitConversionRule(
                biomarker_code="glucose",
                source_unit="mg/dL",
                target_unit="mmol/L",
                conversion_factor=math.inf,
            )

    def test_confidence_out_of_bounds_raises_error(self):
        with pytest.raises(InvalidUnitConversionRuleError, match="confidence must be between 0.0 and 1.0"):
            UnitConversionRule(
                biomarker_code="glucose",
                source_unit="mg/dL",
                target_unit="mmol/L",
                conversion_factor=0.05551,
                confidence=1.5,
            )

    def test_duplicate_rule_registration_raises_error(self):
        normalizer = UnitNormalizer()
        rule1 = UnitConversionRule(
            biomarker_code="glucose",
            source_unit="mg/dL",
            target_unit="mmol/L",
            conversion_factor=0.05551,
        )
        rule2 = UnitConversionRule(
            biomarker_code="glucose",
            source_unit="mg/dL",
            target_unit="mmol/L",
            conversion_factor=0.05551,
        )
        normalizer.register_rule(rule1)
        with pytest.raises(DuplicateUnitConversionRuleError, match="already exists"):
            normalizer.register_rule(rule2)


class TestUnitAliasRegistry:
    def test_unit_alias_normalization(self):
        registry = UnitAliasRegistry()

        assert registry.normalize_unit("  mmol/l  ") == "mmol/L"
        assert registry.normalize_unit("ug/L") == "µg/L"
        assert registry.normalize_unit("μg/L") == "µg/L"
        assert registry.normalize_unit("ng/ml") == "ng/mL"
        assert registry.normalize_unit("miu/l") == "mIU/L"
        assert registry.normalize_unit("u/l") == "U/L"

    def test_unknown_alias_returns_trimmed_original(self):
        registry = UnitAliasRegistry()
        assert registry.normalize_unit("  custom_unit_xyz  ") == "custom_unit_xyz"


class TestUnitNormalizerConversions:
    def test_glucose_conversion(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("glucose", 90.0, "mg/dL")

        assert res.converted is True
        assert res.source_value == 90.0
        assert res.normalized_value == round(90.0 * 0.05551, 6)
        assert res.normalized_unit == "mmol/L"

    def test_hemoglobin_conversion(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("hemoglobin", 14.2, "g/dL")

        assert res.converted is True
        assert res.normalized_value == 142.0
        assert res.normalized_unit == "g/L"

    def test_ferritin_conversion(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("ferritin", 32.0, "ng/mL")

        assert res.converted is True
        assert res.normalized_value == 32.0
        assert res.normalized_unit == "µg/L"

    def test_vitamin_d_conversion(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("vitamin_d_25_oh", 30.0, "ng/mL")

        assert res.converted is True
        assert res.normalized_value == round(30.0 * 2.496, 6)
        assert res.normalized_unit == "nmol/L"

    def test_missing_rule_retains_source_unit(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("ferritin", 50.0, "unknown_unit")

        assert res.converted is False
        assert res.normalized_value == 50.0
        assert res.normalized_unit == "unknown_unit"
        assert res.reason == "no_rule_found_retained_source_unit"

    def test_unresolved_biomarker_code_returns_no_conversion(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert(None, 90.0, "mg/dL")

        assert res.converted is False
        assert res.normalized_value is None
        assert res.normalized_unit is None
        assert res.reason == "unresolved_biomarker_code"

    def test_raw_fields_unmodified_and_no_nan_infinity(self):
        normalizer = create_default_unit_normalizer()
        res = normalizer.convert("glucose", 100.0, "mg/dL")
        assert math.isfinite(res.normalized_value)
        assert res.source_value == 100.0
        assert res.source_unit == "mg/dL"


class TestLaboratoryValueParser:
    def test_parse_integer_and_decimals(self):
        val_int = parse_laboratory_value("90")
        assert val_int.value_type == BiomarkerValueType.NUMERIC
        assert val_int.numeric_value == 90.0

        val_dot = parse_laboratory_value("14.2")
        assert val_dot.value_type == BiomarkerValueType.NUMERIC
        assert val_dot.numeric_value == 14.2

        val_comma = parse_laboratory_value("14,2")
        assert val_comma.value_type == BiomarkerValueType.NUMERIC
        assert val_comma.numeric_value == 14.2

    def test_parse_bounded_inequalities(self):
        val_lt = parse_laboratory_value("< 0.01")
        assert val_lt.value_type == BiomarkerValueType.BOUNDED_INEQUALITY
        assert val_lt.inequality_operator == "<"
        assert val_lt.numeric_value == 0.01

        val_gt = parse_laboratory_value(">1000")
        assert val_gt.value_type == BiomarkerValueType.BOUNDED_INEQUALITY
        assert val_gt.inequality_operator == ">"
        assert val_gt.numeric_value == 1000.0

    def test_parse_range(self):
        val_range = parse_laboratory_value("12 - 16")
        assert val_range.value_type == BiomarkerValueType.RANGE
        assert val_range.range_low == 12.0
        assert val_range.range_high == 16.0

        val_range_unicode = parse_laboratory_value("12–16")
        assert val_range_unicode.value_type == BiomarkerValueType.RANGE
        assert val_range_unicode.range_low == 12.0
        assert val_range_unicode.range_high == 16.0

    def test_parse_qualitative_results(self):
        val_pos = parse_laboratory_value("Obecne")
        assert val_pos.value_type == BiomarkerValueType.QUALITATIVE
        assert val_pos.qualitative_value == "POSITIVE"

        val_neg = parse_laboratory_value("Nieobecne")
        assert val_neg.value_type == BiomarkerValueType.QUALITATIVE
        assert val_neg.qualitative_value == "NEGATIVE"

    def test_parse_text(self):
        val_text = parse_laboratory_value("Przejrzysty")
        assert val_text.value_type == BiomarkerValueType.TEXT
        assert val_text.text_value == "Przejrzysty"

    def test_empty_input_raises_error(self):
        with pytest.raises(InvalidLaboratoryValueError, match="cannot be empty"):
            parse_laboratory_value("   ")

    def test_raw_value_preserved_intact(self):
        raw = "   < 0.01   "
        val = parse_laboratory_value(raw)
        assert val.raw_value == raw


class TestConfidenceComponentsAndEligibility:
    def test_valid_confidence_components(self):
        comp = ConfidenceComponents(
            name_confidence=1.0,
            value_confidence=0.9,
            unit_confidence=1.0,
            reference_confidence=0.8,
            extraction_confidence=0.95,
            verification_status=VerificationStatus.UNVERIFIED,
        )
        assert comp.name_confidence == 1.0
        assert comp.value_confidence == 0.9

    def test_out_of_bounds_confidence_raises_error(self):
        with pytest.raises(InvalidConfidenceComponentError, match="must be a float between 0.0 and 1.0"):
            ConfidenceComponents(name_confidence=1.2)

    def test_rejected_status_ineligible_for_trends(self):
        now = datetime.now(timezone.utc)
        obs = LaboratoryObservation(
            observation_id="obs-01",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            observation_source_fingerprint="fp01",
            raw_name="Ferrytyna",
            raw_value="35",
            raw_unit="µg/L",
            canonical_code="ferritin",
            normalization_status=NormalizationStatus.RESOLVED,
            numeric_value=35.0,
            verification_status=VerificationStatus.REJECTED,
            collected_at=now,
        )
        assessment = evaluate_confidence_eligibility(obs)
        assert assessment.eligible_for_trends is False
        assert assessment.eligible_for_ai_coach is False
        assert "REJECTED" in assessment.reasons[0]

    def test_unverified_status_eligible_for_trends_but_not_ai_coach(self):
        now = datetime.now(timezone.utc)
        obs = LaboratoryObservation(
            observation_id="obs-02",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            observation_source_fingerprint="fp02",
            raw_name="Ferrytyna",
            raw_value="35",
            raw_unit="µg/L",
            canonical_code="ferritin",
            normalization_status=NormalizationStatus.RESOLVED,
            numeric_value=35.0,
            verification_status=VerificationStatus.UNVERIFIED,
            collected_at=now,
        )
        assessment = evaluate_confidence_eligibility(obs)
        assert assessment.eligible_for_trends is True
        assert assessment.eligible_for_ai_coach is False
        assert "UNVERIFIED" in assessment.reasons[0]

    def test_verified_status_eligible_for_ai_coach(self):
        now = datetime.now(timezone.utc)
        obs = LaboratoryObservation(
            observation_id="obs-03",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            observation_source_fingerprint="fp03",
            raw_name="Ferrytyna",
            raw_value="35",
            raw_unit="µg/L",
            canonical_code="ferritin",
            normalization_status=NormalizationStatus.RESOLVED,
            numeric_value=35.0,
            verification_status=VerificationStatus.VERIFIED,
            is_possible_duplicate=False,
            collected_at=now,
        )
        assessment = evaluate_confidence_eligibility(obs)
        assert assessment.eligible_for_trends is True
        assert assessment.eligible_for_ai_coach is True
        assert len(assessment.reasons) == 0

    def test_possible_duplicate_blocks_ai_coach(self):
        now = datetime.now(timezone.utc)
        obs = LaboratoryObservation(
            observation_id="obs-04",
            report_id="rep-01",
            import_run_id="run-01",
            report_row_index=1,
            observation_source_fingerprint="fp04",
            raw_name="Ferrytyna",
            raw_value="35",
            raw_unit="µg/L",
            canonical_code="ferritin",
            normalization_status=NormalizationStatus.RESOLVED,
            numeric_value=35.0,
            verification_status=VerificationStatus.VERIFIED,
            is_possible_duplicate=True,  # Blocks AI Coach
            collected_at=now,
        )
        assessment = evaluate_confidence_eligibility(obs)
        assert assessment.eligible_for_trends is True
        assert assessment.eligible_for_ai_coach is False
        assert "is_possible_duplicate" in assessment.reasons[0]


class TestObservationFactoryIntegration:
    def test_create_laboratory_observation_factory(self):
        registry = create_default_biomarker_registry()
        normalizer = create_default_unit_normalizer()
        now = datetime.now(timezone.utc)

        raw_name = "Glukoza"
        raw_val = "90"
        raw_unit = "mg/dL"

        match = registry.match_alias(raw_name)
        parsed = parse_laboratory_value(raw_val)
        unit_res = normalizer.convert(match.canonical_code, parsed.numeric_value, raw_unit)
        confidence = ConfidenceComponents(verification_status=VerificationStatus.VERIFIED)

        obs = create_laboratory_observation(
            observation_id="obs-factory-1",
            report_id="rep-100",
            import_run_id="run-100",
            report_row_index=1,
            raw_name=raw_name,
            raw_value=raw_val,
            raw_unit=raw_unit,
            source_document_hash="doc_hash_123",
            collected_at=now,
            parsed_value=parsed,
            biomarker_match=match,
            unit_result=unit_res,
            confidence_components=confidence,
        )

        assert obs.canonical_code == "glucose"
        assert obs.raw_name == raw_name
        assert obs.raw_value == raw_val
        assert obs.raw_unit == raw_unit
        assert obs.numeric_value == 90.0
        assert obs.normalized_value == round(90.0 * 0.05551, 6)
        assert obs.normalized_unit == "mmol/L"
        assert obs.platform_message_level == PlatformMessageLevel.INFORMATIONAL
