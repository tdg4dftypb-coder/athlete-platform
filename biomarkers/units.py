"""
Unit Conversion Engine and Unit Alias Registry for Biomarkers.
"""

from dataclasses import dataclass
import math
from typing import Dict, Optional, Tuple

from biomarkers.errors import (
    DuplicateUnitConversionRuleError,
    InvalidUnitConversionRuleError,
)


@dataclass(frozen=True)
class UnitConversionRule:
    """
    Immutable specification for converting a biomarker value from a source unit to a target unit.
    Conversion formula: normalized_value = raw_value * conversion_factor + conversion_offset
    """

    biomarker_code: str
    source_unit: str
    target_unit: str
    rule_version: str = "1.0"
    conversion_factor: float = 1.0
    conversion_offset: float = 0.0
    confidence: float = 1.0
    active: bool = True
    source_reference: str = "standard_unit_conversion"
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.biomarker_code or not self.biomarker_code.strip():
            raise InvalidUnitConversionRuleError("biomarker_code cannot be empty.")
        if not self.source_unit or not self.source_unit.strip():
            raise InvalidUnitConversionRuleError("source_unit cannot be empty.")
        if not self.target_unit or not self.target_unit.strip():
            raise InvalidUnitConversionRuleError("target_unit cannot be empty.")

        src_clean = self.source_unit.strip()
        tgt_clean = self.target_unit.strip()

        if src_clean.lower() == tgt_clean.lower():
            raise InvalidUnitConversionRuleError(
                f"Source unit '{self.source_unit}' and target unit '{self.target_unit}' must be different for a conversion rule."
            )

        if not math.isfinite(self.conversion_factor):
            raise InvalidUnitConversionRuleError("conversion_factor must be a finite float.")
        if not math.isfinite(self.conversion_offset):
            raise InvalidUnitConversionRuleError("conversion_offset must be a finite float.")

        if not (0.0 <= self.confidence <= 1.0):
            raise InvalidUnitConversionRuleError("confidence must be between 0.0 and 1.0.")

        object.__setattr__(self, "biomarker_code", self.biomarker_code.strip().lower())
        object.__setattr__(self, "source_unit", src_clean)
        object.__setattr__(self, "target_unit", tgt_clean)


class UnitAliasRegistry:
    """
    Registry for text normalization of laboratory unit representations.
    Standardizes whitespace, Greek symbols, and typographic capitalization variants safely.
    Preserves raw unit in original observation fields.
    """

    def __init__(self) -> None:
        # Alias map from lowercased raw string to standardized canonical unit string
        self._aliases: Dict[str, str] = {
            # Glucose & mol variants
            "mmol/l": "mmol/L",
            "mmol/L": "mmol/L",
            "mg/dl": "mg/dL",
            "mg/dL": "mg/dL",
            # Hemoglobin & mass/volume variants
            "g/dl": "g/dL",
            "g/dL": "g/dL",
            "g/l": "g/L",
            "g/L": "g/L",
            # Microgram variants (Greek mu, ASCII ug, micro sign µ)
            "ug/l": "µg/L",
            "μg/l": "µg/L",
            "µg/l": "µg/L",
            "ug/L": "µg/L",
            "μg/L": "µg/L",
            "µg/L": "µg/L",
            "ng/ml": "ng/mL",
            "ng/mL": "ng/mL",
            "nmol/l": "nmol/L",
            "nmol/L": "nmol/L",
            # Hormones & International Units
            "miu/l": "mIU/L",
            "miu/L": "mIU/L",
            "mIU/l": "mIU/L",
            "mIU/L": "mIU/L",
            "uiu/ml": "µIU/mL",
            "μiu/ml": "µIU/mL",
            "µiu/ml": "µIU/mL",
            "u/l": "U/L",
            "u/L": "U/L",
            "U/l": "U/L",
            "U/L": "U/L",
        }

    def normalize_unit(self, unit_str: Optional[str]) -> str:
        """
        Normalizes whitespace, Greek symbols, and typography for a unit string.
        Returns trimmed string if no alias match is found.
        """
        if not unit_str or not unit_str.strip():
            return ""
        cleaned = unit_str.strip()
        key = cleaned.lower()
        return self._aliases.get(key, cleaned)

    def register_alias(self, alias_raw: str, canonical_unit: str) -> None:
        """Registers a custom unit alias mapping."""
        if not alias_raw or not alias_raw.strip():
            return
        if not canonical_unit or not canonical_unit.strip():
            return
        self._aliases[alias_raw.strip().lower()] = canonical_unit.strip()


@dataclass(frozen=True)
class UnitNormalizationResult:
    """Immutable result of a unit normalization / conversion operation."""

    converted: bool
    source_value: float
    source_unit: str
    normalized_value: Optional[float]
    normalized_unit: Optional[str]
    biomarker_code: Optional[str]
    rule_version: Optional[str]
    conversion_confidence: float
    reason: str


class UnitNormalizer:
    """
    Versioned Engine for registering and applying explicit biomarker unit conversion rules.
    Converts strictly on exact match (biomarker_code + source_unit + target_unit).
    Never guesses conversions without a rule.
    """

    def __init__(self, alias_registry: Optional[UnitAliasRegistry] = None, version: str = "1.0") -> None:
        self.version = version
        self.alias_registry = alias_registry or UnitAliasRegistry()
        # Key: (biomarker_code.lower(), normalized_source_unit.lower()) -> UnitConversionRule
        self._rules: Dict[Tuple[str, str], UnitConversionRule] = {}

    def register_rule(self, rule: UnitConversionRule) -> None:
        """
        Registers a UnitConversionRule into the normalizer.
        Raises DuplicateUnitConversionRuleError if a rule for the same biomarker and source unit exists.
        """
        src_norm = self.alias_registry.normalize_unit(rule.source_unit).lower()
        key = (rule.biomarker_code.lower(), src_norm)

        if key in self._rules:
            existing = self._rules[key]
            raise DuplicateUnitConversionRuleError(
                f"Rule for biomarker '{rule.biomarker_code}' from source unit '{rule.source_unit}' "
                f"already exists (targets '{existing.target_unit}')."
            )

        self._rules[key] = rule

    def convert(
        self,
        biomarker_code: Optional[str],
        raw_numeric_value: Optional[float],
        raw_unit: str,
    ) -> UnitNormalizationResult:
        """
        Converts a raw numeric value and raw unit to canonical normalized value and unit.
        Does NOT convert unresolved biomarkers or invalid/infinite numeric values.
        Returns explicit UnitNormalizationResult.
        """
        if not raw_unit:
            raw_unit = ""
        source_unit_clean = raw_unit.strip()

        if biomarker_code is None or not biomarker_code.strip():
            return UnitNormalizationResult(
                converted=False,
                source_value=raw_numeric_value if raw_numeric_value is not None else 0.0,
                source_unit=source_unit_clean,
                normalized_value=None,
                normalized_unit=None,
                biomarker_code=None,
                rule_version=None,
                conversion_confidence=0.0,
                reason="unresolved_biomarker_code",
            )

        if raw_numeric_value is None or not math.isfinite(raw_numeric_value):
            return UnitNormalizationResult(
                converted=False,
                source_value=0.0,
                source_unit=source_unit_clean,
                normalized_value=None,
                normalized_unit=None,
                biomarker_code=biomarker_code,
                rule_version=None,
                conversion_confidence=0.0,
                reason="non_numeric_or_missing_value",
            )

        code_key = biomarker_code.strip().lower()
        norm_source_unit = self.alias_registry.normalize_unit(source_unit_clean)
        norm_source_key = norm_source_unit.lower()

        rule = self._rules.get((code_key, norm_source_key))

        if rule and rule.active:
            calc_val = raw_numeric_value * rule.conversion_factor + rule.conversion_offset
            norm_val = round(calc_val, 6)
            norm_target_unit = self.alias_registry.normalize_unit(rule.target_unit)

            return UnitNormalizationResult(
                converted=True,
                source_value=raw_numeric_value,
                source_unit=source_unit_clean,
                normalized_value=norm_val,
                normalized_unit=norm_target_unit,
                biomarker_code=code_key,
                rule_version=rule.rule_version,
                conversion_confidence=rule.confidence,
                reason="conversion_rule_applied",
            )

        # Check if raw unit already equals canonical unit (identity)
        return UnitNormalizationResult(
            converted=False,
            source_value=raw_numeric_value,
            source_unit=source_unit_clean,
            normalized_value=raw_numeric_value,
            normalized_unit=norm_source_unit if norm_source_unit else None,
            biomarker_code=code_key,
            rule_version=None,
            conversion_confidence=1.0,
            reason="no_rule_found_retained_source_unit",
        )


def create_default_unit_normalizer() -> UnitNormalizer:
    """
    Creates a UnitNormalizer pre-loaded with minimal synthetic rules for testing.
    Rules:
    - glucose: mg/dL -> mmol/L (factor: 0.05551)
    - hemoglobin: g/dL -> g/L (factor: 10.0)
    - ferritin: ng/mL -> µg/L (factor: 1.0)
    - vitamin_d_25_oh: ng/mL -> nmol/L (factor: 2.496)
    """
    normalizer = UnitNormalizer(version="1.0")

    seed_rules = [
        UnitConversionRule(
            biomarker_code="glucose",
            source_unit="mg/dL",
            target_unit="mmol/L",
            conversion_factor=0.05551,
            conversion_offset=0.0,
            confidence=1.0,
            source_reference="standard_molar_mass_conversion",
        ),
        UnitConversionRule(
            biomarker_code="hemoglobin",
            source_unit="g/dL",
            target_unit="g/L",
            conversion_factor=10.0,
            conversion_offset=0.0,
            confidence=1.0,
            source_reference="standard_metric_volume_conversion",
        ),
        UnitConversionRule(
            biomarker_code="ferritin",
            source_unit="ng/mL",
            target_unit="µg/L",
            conversion_factor=1.0,
            conversion_offset=0.0,
            confidence=1.0,
            source_reference="identity_mass_per_volume_conversion",
        ),
        UnitConversionRule(
            biomarker_code="vitamin_d_25_oh",
            source_unit="ng/mL",
            target_unit="nmol/L",
            conversion_factor=2.496,
            conversion_offset=0.0,
            confidence=1.0,
            source_reference="standard_molar_mass_conversion",
        ),
    ]

    for rule in seed_rules:
        normalizer.register_rule(rule)

    return normalizer
