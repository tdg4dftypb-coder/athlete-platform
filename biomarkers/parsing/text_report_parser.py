"""
Text Laboratory Report Parser for Polish / European Digital Lab PDF Reports.
Parses ExtractedLaboratoryDocument into RawLaboratoryRow tuples deterministically.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple

from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument
from biomarkers.ingestion import RawLaboratoryRow


@dataclass(frozen=True)
class ParsedReportHeader:
    """Header metadata and accounting metrics extracted from lab report document."""

    laboratory_name: Optional[str] = None
    collected_at: Optional[datetime] = None
    reported_at: Optional[datetime] = None
    warnings: Tuple[str, ...] = ()
    candidate_rows_count: int = 0
    ignored_lines_count: int = 0
    failed_rows_count: int = 0
    extracted_rows_count: int = 0


class TextLaboratoryReportParser:
    """
    Deterministic parser for digital text PDF lab reports.
    Supports table rows, wrapped biomarker names, decimal commas, inequalities, and ranges.
    Adheres strictly to LaboratoryResultParser protocol returning Tuple[RawLaboratoryRow, ...].
    """

    def __init__(self, parser_version: str = "1.0") -> None:
        self.parser_version = parser_version
        self.last_parsed_header: Optional[ParsedReportHeader] = None

    def can_parse(self, document: ExtractedLaboratoryDocument) -> bool:
        """Returns True if document has readable text layer."""
        return document.text_layer_available and len(document.pages) > 0

    def parse(self, document: ExtractedLaboratoryDocument) -> Tuple[RawLaboratoryRow, ...]:
        """
        Parses document pages into raw laboratory rows.
        Attaches header collected_at, reported_at, and laboratory_name to each row.
        """
        if not self.can_parse(document):
            self.last_parsed_header = ParsedReportHeader(warnings=("Document has no readable text layer.",))
            return ()

        full_text_lines: List[Tuple[int, str]] = []
        for page in document.pages:
            for line in page.text.splitlines():
                stripped = line.strip()
                if stripped:
                    full_text_lines.append((page.page_number, stripped))

        header = self._extract_header(full_text_lines)
        self.last_parsed_header = header

        rows = self._extract_rows(
            full_text_lines,
            collected_at=header.collected_at,
            reported_at=header.reported_at,
            laboratory_name=header.laboratory_name,
        )

        return tuple(rows)

    def _extract_header(self, lines: List[Tuple[int, str]]) -> ParsedReportHeader:
        lab_name: Optional[str] = None
        collected_at: Optional[datetime] = None
        reported_at: Optional[datetime] = None
        warnings: List[str] = []

        col_patterns = [
            r"(?:data\s+pobrania|pobrano|data\s+materiału)\s*:?\s*(\d{2}[.-]\d{2}[.-]\d{4}(?:\s+\d{2}:\d{2})?|\d{4}[.-]\d{2}[.-]\d{2}(?:\s+\d{2}:\d{2})?)",
        ]
        rep_patterns = [
            r"(?:data\s+zatwierdzenia|data\s+autoryzacji|data\s+wykonania|zatwierdzono)\s*:?\s*(\d{2}[.-]\d{2}[.-]\d{4}(?:\s+\d{2}:\d{2})?|\d{4}[.-]\d{2}[.-]\d{2}(?:\s+\d{2}:\d{2})?)",
        ]

        for _, line in lines:
            line_lower = line.lower()
            if not lab_name:
                if "synevo" in line_lower:
                    lab_name = "Synevo"
                elif "diagnostyka" in line_lower:
                    lab_name = "Diagnostyka"
                elif "alab" in line_lower:
                    lab_name = "ALAB laboratoria"

            if not collected_at:
                for pat in col_patterns:
                    m = re.search(pat, line, re.IGNORECASE)
                    if m:
                        dt = self._parse_date_str(m.group(1))
                        if dt:
                            collected_at = dt
                            break

            if not reported_at:
                for pat in rep_patterns:
                    m = re.search(pat, line, re.IGNORECASE)
                    if m:
                        dt = self._parse_date_str(m.group(1))
                        if dt:
                            reported_at = dt
                            break

        if not collected_at:
            warnings.append("Collection date (collected_at) could not be unambiguously determined from report header.")

        return ParsedReportHeader(
            laboratory_name=lab_name,
            collected_at=collected_at,
            reported_at=reported_at,
            warnings=tuple(warnings),
        )

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        date_str = date_str.strip()
        formats = [
            "%d.%m.%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d %H:%M",
            "%d.%m.%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _extract_rows(
        self,
        lines: List[Tuple[int, str]],
        collected_at: Optional[datetime] = None,
        reported_at: Optional[datetime] = None,
        laboratory_name: Optional[str] = None,
    ) -> List[RawLaboratoryRow]:
        rows: List[RawLaboratoryRow] = []
        row_idx = 0

        row_regex = re.compile(
            r"^(?P<name>[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\(\)\-\.,]+?)\s+"
            r"(?P<val>[<>]?\s*\d+(?:[\.,]\d+)?|dodatni|ujemny|obecne|nieobecne|przejrzysty)\s+"
            r"(?P<unit>[A-Za-zµμ\%/0-9\^\-]+)?\s*"
            r"(?P<ref>(?:\d+(?:[\.,]\d+)?\s*[\-\–\—]\s*\d+(?:[\.,]\d+)?|[<>]\s*\d+(?:[\.,]\d+)?))?\s*"
            r"(?P<flag>[HL\*])?$",
            re.IGNORECASE,
        )

        pending_name: Optional[str] = None

        for page_num, line in lines:
            line_str = line.strip()
            line_lower = line_str.lower()

            # Skip header / footer lines
            if any(kw in line_lower for kw in ["strona ", "data wydruku", "pesel:", "nr zlecenia:"]):
                continue

            # Skip table header lines
            if "badanie" in line_lower and "wynik" in line_lower:
                continue

            # Pipe separated line
            if "|" in line_str:
                parts = [p.strip() for p in line_str.split("|")]
                if len(parts) >= 2:
                    raw_name = parts[0]
                    raw_val = parts[1]
                    raw_unit = parts[2] if len(parts) > 2 else ""
                    ref_text = parts[3] if len(parts) > 3 else None
                    flag = parts[4] if len(parts) > 4 else None

                    if raw_name and raw_val:
                        rows.append(
                            RawLaboratoryRow(
                                report_row_index=row_idx,
                                raw_name=raw_name,
                                raw_value=raw_val,
                                raw_unit=raw_unit,
                                raw_reference_text=ref_text,
                                raw_flag=flag,
                                collected_at=collected_at,
                                reported_at=reported_at,
                                laboratory_name=laboratory_name,
                            )
                        )
                        row_idx += 1
                        pending_name = None
                        continue

            # Match regular expressions
            m = row_regex.match(line_str)
            if m:
                raw_name = m.group("name").strip()
                if pending_name:
                    raw_name = f"{pending_name} {raw_name}"
                    pending_name = None

                raw_val = m.group("val").strip()
                raw_unit = (m.group("unit") or "").strip()
                ref_text = (m.group("ref") or "").strip() or None
                flag = (m.group("flag") or "").strip() or None

                rows.append(
                    RawLaboratoryRow(
                        report_row_index=row_idx,
                        raw_name=raw_name,
                        raw_value=raw_val,
                        raw_unit=raw_unit,
                        raw_reference_text=ref_text,
                        raw_flag=flag,
                        collected_at=collected_at,
                        reported_at=reported_at,
                        laboratory_name=laboratory_name,
                    )
                )
                row_idx += 1
                continue

            # If line is a wrapped biomarker name (e.g. "(25-OH)" or "w surowicy")
            if len(line_str) < 40 and not any(char.isdigit() for char in line_str):
                # Skip header/organization names
                if not any(k in line_lower for k in ["sp. z o.o.", "laboratorium", "al. ", "ul. ", "pobrania", "zatwierdzenia", "diagnostyka", "synevo", "alab"]):
                    pending_name = f"{pending_name} {line_str}" if pending_name else line_str

        return rows
