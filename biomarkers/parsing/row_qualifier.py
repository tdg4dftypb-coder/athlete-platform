"""
Laboratory Result Row Qualifier and PII Filtering Engine for Biomarkers Domain.
Determines whether a candidate document text line represents a credible lab result row.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional, Set, Tuple


class RowQualificationStatus(Enum):
    QUALIFIED_RESULT = "qualified_result"
    IGNORED_PII_ADMIN = "ignored_pii_admin"
    IGNORED_NOISE_HEADER = "ignored_noise_header"
    MALFORMED_RESULT = "malformed_result"


@dataclass(frozen=True)
class QualificationResult:
    status: RowQualificationStatus
    reason_code: str


class LaboratoryResultRowQualifier:
    """
    Qualifies candidate text lines strictly into lab result rows vs non-result administrative/PII lines.
    Enforces that LaboratoryObservation records are created ONLY for structurally valid test results.
    """

    ADMIN_PII_PATTERNS = (
        r"\bpesel\b",
        r"\bdata\s+urodzenia\b",
        r"\badres\b",
        r"\bident\.\s*pacjenta\b",
        r"\bident\.\s*dokumentu\b",
        r"\bid\s*pacjenta\b",
        r"\bpacjent\s*:",
        r"\blekarz\b",
        r"\bzleceniodawca\b",
        r"\bwykonali\b",
        r"\bzatwierdził\b",
        r"\bzatwierdzili\b",
        r"\bautoryzował\b",
        r"\bdiagnosta\b",
        r"\bmgr\b",
        r"\blek\.\s*med\b",
        r"\bdr\s+hab\b",
        r"\btel\.",
        r"\bfax\b",
        r"\be-mail",
        r"\bemail\b",
        r"\bdata\s+i\s+godzina\s+wydania\b",
        r"\bdata\s+wydruku\b",
        r"\bstrona\s+\d+",
        r"\bpunkt\s+pobrań\b",
        r"\blaboratorium\s+analiz\b",
        r"\balab\s+laboratoria\b",
        r"\bsp\.\s*z\s*o\.o\.",
        r"\bul\.\s*",
        r"\bal\.\s*",
        r"\bidentyfikacja\s+pacjenta\b",
        r"\bmetoda\b",
        r"\banalizator\b",
    )

    QUALITATIVE_VALUES = {
        "nieobecny", "obecny", "dodatni", "ujemny", "nieobecne", "obecne",
        "przejrzysty", "prawidłowy", "nieprawidłowy", "wykryto", "nie wykryto"
    }

    UNITLESS_BIOMARKER_KEYWORDS = {
        "inr", "wskaźnik inr", "wskaźnik protrombinowy", "wskaźnik pt",
        "homa-ir", "ph", "ciężar właściwy"
    }

    def __init__(self) -> None:
        self._pii_regex = re.compile("|".join(self.ADMIN_PII_PATTERNS), re.IGNORECASE)

    def qualify(self, line_str: str, pending_name: Optional[str] = None) -> QualificationResult:
        """
        Qualifies a candidate text line.
        Returns QualificationResult with status and controlled reason code.
        """
        line_clean = line_str.strip()
        if not line_clean:
            return QualificationResult(RowQualificationStatus.IGNORED_NOISE_HEADER, "EMPTY_LINE")

        # 1. Reject Administrative & PII Lines
        if self._pii_regex.search(line_clean):
            return QualificationResult(RowQualificationStatus.IGNORED_PII_ADMIN, "NON_RESULT_LINE_IGNORED")

        line_lower = line_clean.lower()

        # 2. Reject Section Headers & Noise
        if any(h in line_lower for h in ["badanie wynik", "zakres referencyjny", "morfologia krwi", "układ krzepnięcia", "biochemia"]):
            return QualificationResult(RowQualificationStatus.IGNORED_NOISE_HEADER, "HEADER_OR_SECTION_LINE")

        if line_clean.endswith("/"):
            return QualificationResult(RowQualificationStatus.IGNORED_NOISE_HEADER, "GROUP_TITLE_LINE")

        # 3. Check Qualification Criteria A (Standard Result: Name + Value + Unit)
        std_pattern = re.compile(
            r"^(?P<name>[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż\(\)][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\(\)\-\/\.,%#\+]*?)\s+"
            r"(?P<val>[<>]?\s*\d+(?:[\.,]\d+)?)\s*"
            r"(?P<unit>[A-Za-zµμ\%/0-9\^\-\#\*\+]+(?:\s+FEU)?)\s*",
            re.IGNORECASE,
        )
        if std_pattern.match(line_clean):
            return QualificationResult(RowQualificationStatus.QUALIFIED_RESULT, "STANDARD_RESULT")

        # 4. Check Qualification Criteria B (Qualitative Result)
        qual_pattern = re.compile(
            r"^(?P<name>[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż\(\)][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\(\)\-\/\.,%#\+]*?)\s+"
            r"(?P<val>nieobecny|obecny|dodatni|ujemny|nieobecne|obecne|przejrzysty|prawidłowy|nieprawidłowy)",
            re.IGNORECASE,
        )
        if qual_pattern.match(line_clean):
            return QualificationResult(RowQualificationStatus.QUALIFIED_RESULT, "QUALITATIVE_RESULT")

        # 5. Check Qualification Criteria C (Unitless Marker, e.g. INR 1,02)
        if any(kw in line_lower for kw in self.UNITLESS_BIOMARKER_KEYWORDS):
            unitless_pattern = re.compile(
                r"^(?P<name>[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż\(\)][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\(\)\-\/\.,%#\+]*?)\s+"
                r"(?P<val>[<>]?\s*\d+(?:[\.,]\d+)?)",
                re.IGNORECASE,
            )
            if unitless_pattern.match(line_clean):
                return QualificationResult(RowQualificationStatus.QUALIFIED_RESULT, "UNITLESS_RESULT")

        # 6. Check Qualification Criteria D (Multiline Result with Pending Name)
        if pending_name:
            multiline_pattern = re.compile(
                r"^(?P<val>[<>]?\s*\d+(?:[\.,]\d+)?|nieobecny|obecny|dodatni|ujemny|nieobecne|obecne)\s*"
                r"(?P<unit>[A-Za-zµμ\%/0-9\^\-\#\*\+]+(?:\s+FEU)?)?",
                re.IGNORECASE,
            )
            if multiline_pattern.match(line_clean):
                return QualificationResult(RowQualificationStatus.QUALIFIED_RESULT, "MULTILINE_RESULT")

        # 7. Check if line is a multiline name buffer candidate (e.g. Czas kaolinowo-kefalinowy (APTT))
        line_no_tag = re.sub(r"\([A-Z]\d{1,4}\)", "", line_clean, flags=re.IGNORECASE)
        if len(line_clean) < 70 and not any(c.isdigit() for c in line_no_tag):
            if any(c.isalpha() for c in line_clean):
                return QualificationResult(RowQualificationStatus.IGNORED_NOISE_HEADER, "MULTILINE_NAME_BUFFER")

        # Fallback: line failed result qualification
        return QualificationResult(RowQualificationStatus.IGNORED_NOISE_HEADER, "NON_RESULT_LINE_IGNORED")
