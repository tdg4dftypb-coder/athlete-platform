"""
Versioned Biomarker Registry and Alias Matching engine.
"""

from dataclasses import dataclass
import re
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

    def list_all(self, include_inactive: bool = False) -> list[BiomarkerDefinition]:
        """Returns all registered biomarker definitions."""
        if include_inactive:
            return list(self._definitions.values())
        return [d for d in self._definitions.values() if d.active]

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

    def match_alias(
        self,
        raw_name: str,
        raw_unit: Optional[str] = None,
        raw_value: Optional[str] = None,
        include_inactive: bool = False,
    ) -> BiomarkerMatch:
        """
        Matches a raw laboratory name string against registered aliases.
        Case-insensitive and trimmed with unit/value context fallback.
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

        raw_name_clean = re.sub(r"\s*\([A-Z]\d{2,4}\)", "", raw_name.strip(), flags=re.IGNORECASE)
        raw_key = raw_name_clean.lower()
        target_code = self._alias_index.get(raw_key)

        # Contextual Fallback for RDW (rdw_cv vs rdw_sd)
        if not target_code or target_code in ("rdw_cv", "rdw_sd"):
            if "rdw" in raw_key or "anizocytozy erytrocytów" in raw_key:
                clean_u = (raw_unit or "").strip().lower()
                if clean_u in ("fl", "femtoliter") or "sd" in raw_key:
                    target_code = "rdw_sd"
                elif clean_u == "%" or "cv" in raw_key or "rdw" in raw_key:
                    target_code = "rdw_cv"

        # Contextual Fallback for HBsAg (hbs_antigen_numeric vs hbs_antigen_qualitative)
        if not target_code or target_code in ("hbs_antigen_numeric", "hbs_antigen_qualitative"):
            if "hbs" in raw_key or "antygen hbs" in raw_key:
                clean_v = (raw_value or "").strip().lower()
                clean_u = (raw_unit or "").strip().lower()
                if clean_v in ("nieobecny", "obecny", "ujemny", "dodatni") or clean_u == "":
                    target_code = "hbs_antigen_qualitative"
                else:
                    target_code = "hbs_antigen_numeric"

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
    Creates a BiomarkerRegistry seeded with comprehensive biomarker definitions
    supporting ALAB, Synevo, and Diagnostyka Polish lab report formats.
    """
    registry = BiomarkerRegistry(version="1.0")

    seed_definitions = [
        # --- Basic / Chemistry ---
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
            accepted_aliases=("witamina d 25-oh", "25-oh vitamin d", "calcidiol", "wit d 25-oh", "witamina d (25-oh)"),
            accepted_units=("ng/mL", "nmol/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),

        # --- Morphology ---
        BiomarkerDefinition(
            canonical_code="leukocytes",
            canonical_name="Leukocyty",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("leukocyty", "wbc", "leukocyty (wbc)", "leukocyty / wbc", "wbc / leukocyty"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="erythrocytes",
            canonical_name="Erytrocyty",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^6/µL",
            accepted_aliases=("erytrocyty", "rbc", "erytrocyty (rbc)", "erytrocyty / rbc", "rbc / erytrocyty"),
            accepted_units=("10^6/µL", "10*6/uL", "10^6/ul", "mill/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="hemoglobin",
            canonical_name="Hemoglobina",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="g/dL",
            accepted_aliases=("hemoglobina", "hgb", "hb", "hemoglobina (hgb)", "hemoglobina / hgb", "hgb / hemoglobina"),
            accepted_units=("g/dL", "g/L", "mmol/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="hematocrit",
            canonical_name="Hematokryt",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("hematokryt", "hct", "hematokryt (hct)", "hematokryt / hct", "hct / hematokryt"),
            accepted_units=("%", "l/l"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="mcv",
            canonical_name="MCV",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="fL",
            accepted_aliases=("mcv", "wskaźnik mcv", "średnia objętość krwinki (mcv)", "średnia objętość erytrocyta (mcv)"),
            accepted_units=("fL", "fl"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="mch",
            canonical_name="MCH",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="pg",
            accepted_aliases=("mch", "wskaźnik mch", "średnia masa hemoglobonu (mch)", "średnia masa hgb w erytrocycie (mch)"),
            accepted_units=("pg",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="mchc",
            canonical_name="MCHC",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="g/dL",
            accepted_aliases=("mchc", "wskaźnik mchc", "średnie stężenie hgb (mchc)", "średnie stężenie hgb w erytrocytach (mchc)"),
            accepted_units=("g/dL", "g/L", "mmol/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="rdw_cv",
            canonical_name="RDW-CV",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("rdw-cv", "rdw cv", "wskaźnik rdw-cv", "rdw_cv", "wskaźnik anizocytozy erytrocytów (rdw)"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="rdw_sd",
            canonical_name="RDW-SD",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="fL",
            accepted_aliases=("rdw-sd", "rdw sd", "wskaźnik rdw-sd", "rdw_sd"),
            accepted_units=("fL", "fl"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="platelets",
            canonical_name="Płytki krwi",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("płytki krwi", "plt", "płytki krwi (plt)", "płytki krwi / plt", "plt / płytki krwi"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="pct",
            canonical_name="PCT",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("pct", "hematokryt płytkowy", "hematokryt płytkowy (pct)", "płytkokryt (pct)", "płytkokryt"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="pdw",
            canonical_name="PDW",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="fL",
            accepted_aliases=("pdw", "wskaźnik pdw", "dyspersja anizocytozy płytek (pdw)", "wskaźnik anizocytozy płytek krwi (pdw)"),
            accepted_units=("fL", "fl", "%"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="mpv",
            canonical_name="MPV",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="fL",
            accepted_aliases=("mpv", "średnia objętość płytki", "średnia objętość płytki (mpv)", "średnia objętość płytki krwi (mpv)"),
            accepted_units=("fL", "fl"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="large_platelet_ratio",
            canonical_name="Duże płytki krwi",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("p-lcc", "p-lcr", "duże płytki krwi", "duże płytki (p-lcr)", "duże płytki (p-lcc)", "odsetek płytek dużych"),
            accepted_units=("%", "10^3/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="neutrophils_percent",
            canonical_name="Neutrofile %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("neutrofile %", "neut%", "neutrocyty %", "neutrofile wyliczone %", "neutrocyty (neu%)"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="lymphocytes_percent",
            canonical_name="Limfocyty %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("limfocyty %", "lymph%", "limfocyty wyliczone %", "limfocyty (lymph%)"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="monocytes_percent",
            canonical_name="Monocyty %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("monocyty %", "mono%", "monocyty wyliczone %", "monocyty (mon%)"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="eosinophils_percent",
            canonical_name="Eozynofile %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("eozynofile %", "eo%", "eozynofile wyliczone %", "eozynocyty (eos%)", "eozynocyty %"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="basophils_percent",
            canonical_name="Bazofile %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("bazofile %", "baso%", "bazofile wyliczone %", "bazocyty (baso%)", "bazocyty %"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="immature_granulocytes_percent",
            canonical_name="Granulocyty niedojrzałe %",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="%",
            accepted_aliases=("ig%", "granulocyty niedojrzałe %", "młode formy granulocytów %", "niedojrzałe granulocyty %"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="neutrophils_absolute",
            canonical_name="Neutrofile #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("neutrofile #", "neut#", "neutrocyty #", "neutrofile ilość", "neutrofile (ilość)", "neutrocyty (neu)"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="lymphocytes_absolute",
            canonical_name="Limfocyty #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("limfocyty #", "lymph#", "limfocyty ilość", "limfocyty (ilość)", "limfocyty (lymph)"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="monocytes_absolute",
            canonical_name="Monocyty #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("monocyty #", "mono#", "monocyty ilość", "monocyty (ilość)", "monocyty (mon)"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="eosinophils_absolute",
            canonical_name="Eozynofile #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("eozynofile #", "eo#", "eozynofile ilość", "eozynofile (ilość)", "eozynocyty (eos)", "eozynocyty"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="basophils_absolute",
            canonical_name="Bazofile #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("bazofile #", "baso#", "bazofile ilość", "bazofile (ilość)", "bazocyty (baso)", "bazocyty"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="immature_granulocytes_absolute",
            canonical_name="Granulocyty niedojrzałe #",
            category=BiomarkerCategory.MORPHOLOGY,
            default_unit="10^3/µL",
            accepted_aliases=("ig#", "granulocyty niedojrzałe #", "granulocyty niedojrzałe ilość", "niedojrzałe granulocyty"),
            accepted_units=("10^3/µL", "10*3/uL", "10^3/ul", "thou/µL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),

        # --- Coagulation ---
        BiomarkerDefinition(
            canonical_code="aptt",
            canonical_name="APTT",
            category=BiomarkerCategory.OTHER,
            default_unit="s",
            accepted_aliases=("aptt", "czas kaolinowo-kefalinowy", "czas kaolinowo-kefalinowy (aptt)", "czas kaolinowo - kefalinowy", "czas kaolinowo - kefalinowy (aptt)"),
            accepted_units=("s", "sek", "sek."),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="prothrombin_time",
            canonical_name="Czas protrombinowy (PT)",
            category=BiomarkerCategory.OTHER,
            default_unit="s",
            accepted_aliases=("czas protrombinowy", "pt", "czas protrombinowy (pt)"),
            accepted_units=("s", "sek", "sek."),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="prothrombin_index",
            canonical_name="Wskaźnik protrombinowy",
            category=BiomarkerCategory.OTHER,
            default_unit="%",
            accepted_aliases=("wskaźnik protrombinowy", "wskaźnik pt"),
            accepted_units=("%",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="inr",
            canonical_name="INR",
            category=BiomarkerCategory.OTHER,
            default_unit="",
            accepted_aliases=("inr", "wskaźnik inr"),
            accepted_units=("",),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="d_dimer",
            canonical_name="D-dimer",
            category=BiomarkerCategory.INFLAMMATORY_MARKERS,
            default_unit="ng/mL",
            accepted_aliases=("d-dimer", "d-dimery", "d-dimer feu", "stężenie d-dimerów"),
            accepted_units=("ng/mL", "ng/ml", "ng/ml feu", "ng/mL FEU", "µg/L", "ug/L"),
            value_type=BiomarkerValueType.NUMERIC,
        ),

        # --- Immunochemistry ---
        BiomarkerDefinition(
            canonical_code="hbs_antigen_numeric",
            canonical_name="HBsAg (ilościowo)",
            category=BiomarkerCategory.OTHER,
            default_unit="S/CO",
            accepted_aliases=("hbsag ilościowo", "hbs-antygen ilościowo", "hbs-antygen (hbsag) - ilościowo", "hbsag numeric", "hbs-antygen (hbsag) ilościowo", "hbs - antygen hbs (wzw typu b)"),
            accepted_units=("S/CO", "s/co", "IU/mL"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
        BiomarkerDefinition(
            canonical_code="hbs_antigen_qualitative",
            canonical_name="HBsAg (jakościowo)",
            category=BiomarkerCategory.OTHER,
            default_unit="",
            accepted_aliases=("hbsag jakościowo", "hbs-antygen jakościowo", "hbs-antygen (hbsag) - jakościowo", "hbsag qualitative", "hbs-antygen (hbsag) jakościowo"),
            accepted_units=("",),
            value_type=BiomarkerValueType.QUALITATIVE,
        ),
        BiomarkerDefinition(
            canonical_code="crp",
            canonical_name="Białko C-reaktywne (CRP)",
            category=BiomarkerCategory.INFLAMMATORY_MARKERS,
            default_unit="mg/L",
            accepted_aliases=("crp", "białko c-reaktywne", "białko c-reaktywne (crp)", "białko ostrej fazy (crp)"),
            accepted_units=("mg/L", "mg/l"),
            value_type=BiomarkerValueType.NUMERIC,
        ),
    ]

    for def_item in seed_definitions:
        registry.register(def_item)

    return registry
