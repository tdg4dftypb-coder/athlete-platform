"""
Laboratory Raw Value Parser Engine.
"""

from dataclasses import dataclass
import re
from typing import Optional, Tuple

from biomarkers.errors import InvalidLaboratoryValueError
from biomarkers.models import BiomarkerValueType


@dataclass(frozen=True)
class ParsedLaboratoryValue:
    """Immutable result of parsing a raw laboratory value string."""

    raw_value: str
    value_type: BiomarkerValueType
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    qualitative_value: Optional[str] = None
    inequality_operator: Optional[str] = None  # "<", ">", "<=", ">="
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    parse_status: str = "success"
    warnings: Tuple[str, ...] = ()


def parse_laboratory_value(raw_val: str) -> ParsedLaboratoryValue:
    """
    Parses a raw laboratory value string into structured domain representation.
    
    Supported formats:
    - Decimal points & commas: "14.2", "14,2", "90" -> NUMERIC
    - Bounded inequalities: "< 0.01", ">1000", "<= 5", ">= 10" -> BOUNDED_INEQUALITY
    - Ranges: "12 - 16", "12–16" -> RANGE
    - Qualitative results: "POSITIVE", "NEGATIVE", "Obecne", "Nieobecne", "Dodatni", "Ujemny" -> QUALITATIVE
    - Free text: "Przejrzysty", "Żółty" -> TEXT
    
    Raises InvalidLaboratoryValueError on empty or whitespace input.
    """
    if raw_val is None or not str(raw_val).strip():
        raise InvalidLaboratoryValueError("raw_value cannot be empty or whitespace.")

    raw_str = str(raw_val)
    clean_str = raw_str.strip()

    # 1. Qualitative check (check NEGATIVE before POSITIVE because 'nieobecne' contains 'obecne')
    qual_lower = clean_str.lower()
    negative_terms = {"negative", "nieobecne", "ujemny", "ujemna", "ujemne", "nieobecna", "nieobecny", "norma", "neg", "(-)"}
    positive_terms = {"positive", "obecne", "dodatni", "dodatnia", "dodatnie", "obecna", "obecny", "pos", "(+)"}

    if qual_lower in negative_terms or clean_str in ("(-)", "neg (-)"):
        return ParsedLaboratoryValue(
            raw_value=raw_str,
            value_type=BiomarkerValueType.QUALITATIVE,
            qualitative_value="NEGATIVE",
            parse_status="success",
        )

    if qual_lower in positive_terms or clean_str in ("(+)", "pos (+)"):
        return ParsedLaboratoryValue(
            raw_value=raw_str,
            value_type=BiomarkerValueType.QUALITATIVE,
            qualitative_value="POSITIVE",
            parse_status="success",
        )

    # 2. Bounded Inequality check (< 0.01, >1000, <= 5.0, >= 10.5)
    inequality_match = re.match(r"^(<=|>=|<|>)\s*([0-9]+(?:[\.,][0-9]+)?)$", clean_str)
    if inequality_match:
        op, num_str = inequality_match.groups()
        num_clean = num_str.replace(",", ".")
        try:
            val_float = float(num_clean)
            return ParsedLaboratoryValue(
                raw_value=raw_str,
                value_type=BiomarkerValueType.BOUNDED_INEQUALITY,
                numeric_value=val_float,
                inequality_operator=op,
                parse_status="success",
            )
        except ValueError:
            pass

    # 3. Range check (12 - 16, 12–16)
    range_match = re.match(r"^([0-9]+(?:[\.,][0-9]+)?)\s*[\-–—]\s*([0-9]+(?:[\.,][0-9]+)?)$", clean_str)
    if range_match:
        low_str, high_str = range_match.groups()
        try:
            low_val = float(low_str.replace(",", "."))
            high_val = float(high_str.replace(",", "."))
            return ParsedLaboratoryValue(
                raw_value=raw_str,
                value_type=BiomarkerValueType.RANGE,
                range_low=low_val,
                range_high=high_val,
                parse_status="success",
            )
        except ValueError:
            pass

    # 4. Single Numeric check (14.2, 14,2, 90)
    numeric_match = re.match(r"^[+-]?([0-9]+(?:[\.,][0-9]+)?)$", clean_str)
    if numeric_match:
        num_clean = numeric_match.group(1).replace(",", ".")
        try:
            val_float = float(num_clean)
            return ParsedLaboratoryValue(
                raw_value=raw_str,
                value_type=BiomarkerValueType.NUMERIC,
                numeric_value=val_float,
                parse_status="success",
            )
        except ValueError:
            pass

    # 5. Free Text check (Przejrzysty, Żółty)
    if not re.search(r"[\{\}\[\]\\\/]", clean_str):
        return ParsedLaboratoryValue(
            raw_value=raw_str,
            value_type=BiomarkerValueType.TEXT,
            text_value=clean_str,
            parse_status="success",
        )

    # 6. Unrecognized / Invalid fallback
    return ParsedLaboratoryValue(
        raw_value=raw_str,
        value_type=BiomarkerValueType.TEXT,
        text_value=clean_str,
        parse_status="failed",
        warnings=(f"Unrecognized laboratory value format: '{raw_str}'",),
    )
