"""
Versioned Biomarker Registry and Alias Matching engine.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set

from biomarkers.errors import DuplicateAliasError, DuplicateCanonicalCodeError
from biomarkers.models import (
    BiomarkerCategory,
    BiomarkerDefinition,
    BiomarkerValueType,
    NormalizationStatus,
)


@dataclass(frozen=True)
class BiomarkerMatch:
    """Immutable result of a biomarker alias lookup in BiomarkerRegistry."""

    canonical_code: Optional[str]
    definition: Optional[BiomarkerDefinition]
    normalization_status: NormalizationStatus
    alias_match_confidence: float
    matched_alias: Optional[str]
    requires_review: bool


class BiomarkerRegistry:
    """
    Versioned registry of canonical biomarker definitions.
    Manages registration, alias collision detection, and exact alias resolution.
    """

    def __init__(self, version: str = "1.0") -> None:
        self.version = version
        self._definitions: Dict[str, BiomarkerDefinition] = {}
        # Mapping from lowercased alias/canonical_code to canonical_code
        self._alias_index: Dict[str, str] = {}
        # Map lowercased alias to exact preserved alias string
        self._exact_alias_str: Dict[str, str] = {}

    def register(self, definition: BiomarkerDefinition) -> None:
        """
        Registers a new BiomarkerDefinition into the registry.
        Checks for canonical_code and alias collisions.
        """
        code_key = definition.canonical_code.lower()

        if code_key in self._definitions:
            raise DuplicateCanonicalCodeError(
                f"Canonical code '{definition.canonical_code}' is already registered in registry v{self.version}."
            )

        # Check code collision against existing aliases
        if code_key in self._alias_index:
            existing_code = self._alias_index[code_key]
            raise DuplicateAliasError(
                f"Canonical code '{definition.canonical_code}' collides with an existing alias for '{existing_code}'."
            )

        # Check alias collisions against existing codes and aliases
        alias_keys_for_def: Set[str] = {code_key}
        for alias in definition.accepted_aliases:
            alias_key = alias.strip().lower()
            if not alias_key:
                continue
            if alias_key in self._alias_index:
                existing_code = self._alias_index[alias_key]
                raise DuplicateAliasError(
                    f"Alias '{alias}' in definition '{definition.canonical_code}' collides with registered alias for '{existing_code}'."
                )
            alias_keys_for_def.add(alias_key)

        # Register definition
        self._definitions[code_key] = definition

        # Index code and aliases
        self._alias_index[code_key] = code_key
        self._exact_alias_str[code_key] = definition.canonical_name

        for alias in definition.accepted_aliases:
            cleaned = alias.strip()
            if not cleaned:
                continue
            alias_key = cleaned.lower()
            self._alias_index[alias_key] = code_key
            self._exact_alias_str[alias_key] = cleaned

    def get(self, canonical_code: str, include_inactive: bool = False) -> Optional[BiomarkerDefinition]:
        """Looks up a definition by canonical_code."""
        if not canonical_code:
            return None
        code_key = canonical_code.strip().lower()
        definition = self._definitions.get(code_key)
        if not definition:
            return None
        if not definition.active and not include_inactive:
            return None
        return definition

    def match_alias(self, raw_name: str, include_inactive: bool = False) -> BiomarkerMatch:
        """
        Matches a raw laboratory name string against registered aliases.
        Case-insensitive and trimmed. NO fuzzy matching in this sprint.
        Returns explicit BiomarkerMatch object.
        """
        if not raw_name or not raw_name.strip():
            return BiomarkerMatch(
                canonical_code=None,
                definition=None,
                normalization_status=NormalizationStatus.UNRESOLVED,
                alias_match_confidence=0.0,
                matched_alias=None,
                requires_review=True,
            )

        raw_key = raw_name.strip().lower()
        target_code = self._alias_index.get(raw_key)

        if not target_code:
            return BiomarkerMatch(
                canonical_code=None,
                definition=None,
                normalization_status=NormalizationStatus.UNRESOLVED,
                alias_match_confidence=0.0,
                matched_alias=None,
                requires_review=True,
            )

        definition = self._definitions.get(target_code)
        if not definition:
            return BiomarkerMatch(
                canonical_code=None,
                definition=None,
                normalization_status=NormalizationStatus.UNRESOLVED,
                alias_match_confidence=0.0,
                matched_alias=None,
                requires_review=True,
            )

        if not definition.active and not include_inactive:
            return BiomarkerMatch(
                canonical_code=None,
                definition=None,
                normalization_status=NormalizationStatus.UNRESOLVED,
                alias_match_confidence=0.0,
                matched_alias=None,
                requires_review=True,
            )

        matched_str = self._exact_alias_str.get(raw_key, raw_name.strip())
        return BiomarkerMatch(
            canonical_code=definition.canonical_code,
            definition=definition,
            normalization_status=NormalizationStatus.RESOLVED,
            alias_match_confidence=1.0,
            matched_alias=matched_str,
            requires_review=False,
        )

    def list_definitions(self, include_inactive: bool = False) -> Tuple[BiomarkerDefinition, ...]:
        """Returns all registered definitions."""
        if include_inactive:
            return tuple(self._definitions.values())
        return tuple(d for d in self._definitions.values() if d.active)


def create_default_biomarker_registry() -> BiomarkerRegistry:
    """
    Creates a BiomarkerRegistry seeded with a minimal synthetic set of 5 biomarkers
    for testing and domain validation.
    """
    registry = BiomarkerRegistry(version="1.0")

    seed_definitions = [
        BiomarkerDefinition(
            canonical_code="glucose",
            canonical_name="Glukoza",
            category=BiomarkerCategory.OTHER,
            default_unit="mmol/L",
            accepted_aliases=("glukoza", "glucose", "glu", "glukoza na czczo"),
            accepted_units=("mmol/L", "mg/dL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="hemoglobin",
            canonical_name="Hemoglobina",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="g/dL",
            accepted_aliases=("hemoglobina", "hgb", "hb", "hemoglobin"),
            accepted_units=("g/dL", "g/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="ferritin",
            canonical_name="Ferrytyna",
            category=BiomarkerCategory.IRON_PANEL,
            default_unit="µg/L",
            accepted_aliases=("ferrytyna", "ferritin", "fer"),
            accepted_units=("µg/L", "ng/mL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="tsh",
            canonical_name="TSH",
            category=BiomarkerCategory.HORMONES,
            default_unit="mIU/L",
            accepted_aliases=("tsh", "thyrotropin", "hormon thyreotropowy"),
            accepted_units=("mIU/L", "µIU/mL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="vitamin_d_25_oh",
            canonical_name="Witamina D 25-OH",
            category=BiomarkerCategory.VITAMINS,
            default_unit="ng/mL",
            accepted_aliases=("witamina d 25-oh", "25-oh vitamin d", "calcidiol", "wit d 25-oh"),
            accepted_units=("ng/mL", "nmol/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
    ]

    for def_item in seed_definitions:
        registry.register(def_item)

    return registry
