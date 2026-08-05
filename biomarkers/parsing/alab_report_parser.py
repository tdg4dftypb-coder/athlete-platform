"""
ALAB Specialized Laboratory PDF Text Report Parser.
Supports multi-line layout, grouped headers, single-sided reference ranges,
and strict collected_at extraction.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple

from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument
from biomarkers.ingestion import RawLaboratoryRow
from biomarkers.parsing.text_report_parser import ParsedReportHeader


class AlabTextLaboratoryReportParser:
    """
    Specialized parser for ALAB Laboratoria text PDF reports.
    """

    def __init__(self, parser_version: str = "1.0") -> None:
        self.parser_version = parser_version
        self.last_parsed_header: Optional[ParsedReportHeader] = None

    def can_parse(self, document: ExtractedLaboratoryDocument) -> bool:
        """Returns True if document text contains ALAB signatures."""
        if not document.text_layer_available or not document.pages:
            return False

        full_text = "\n".join(p.text for p in document.pages).lower()
        return "alab" in full_text or "data i godz. pobrania:" in full_text

    def parse(self, document: ExtractedLaboratoryDocument) -> Tuple[RawLaboratoryRow, ...]:
        if not self.can_parse(document):
            self.last_parsed_header = ParsedReportHeader(warnings=("Document is not a recognized ALAB report.",))
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
            laboratory_name=header.laboratory_name or "ALAB laboratoria",
        )

        return tuple(rows)

    def _extract_header(self, lines: List[Tuple[int, str]]) -> ParsedReportHeader:
        collected_dates: List[datetime] = []
        reported_dates: List[datetime] = []
        warnings: List[str] = []

        col_pattern = re.compile(
            r"data\s+i\s+godz\.\s+pobrania\s*:?\s*(\d{2}[.-]\d{2}[.-]\d{4}(?:\s+\d{2}:\d{2})?)",
            re.IGNORECASE,
        )
        rep_pattern = re.compile(
            r"(?:data\s+zatwierdzenia|data\s+autoryzacji|data\s+wykonania)\s*:?\s*(\d{2}[.-]\d{2}[.-]\d{4}(?:\s+\d{2}:\d{2})?)",
            re.IGNORECASE,
        )

        for _, line in lines:
            m_col = col_pattern.search(line)
            if m_col:
                dt = self._parse_date_str(m_col.group(1))
                if dt and dt not in collected_dates:
                    collected_dates.append(dt)

            m_rep = rep_pattern.search(line)
            if m_rep:
                dt = self._parse_date_str(m_rep.group(1))
                if dt and dt not in reported_dates:
                    reported_dates.append(dt)

        final_collected: Optional[datetime] = None
        if len(collected_dates) == 1:
            final_collected = collected_dates[0]
        elif len(collected_dates) > 1:
            warnings.append(f"Multiple different collection dates found in document ({len(collected_dates)} distinct dates).")
        else:
            warnings.append("Collection date (collected_at) could not be determined from ALAB report header.")

        final_reported = reported_dates[0] if reported_dates else None

        return ParsedReportHeader(
            laboratory_name="ALAB laboratoria",
            collected_at=final_collected,
            reported_at=final_reported,
            warnings=tuple(warnings),
        )

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        date_str = date_str.strip()
        formats = [
            "%d-%m-%Y %H:%M",
            "%d.%m.%Y %H:%M",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y-%m-%d %H:%M",
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
        laboratory_name: Optional[str] = "ALAB laboratoria",
    ) -> List[RawLaboratoryRow]:
        rows: List[RawLaboratoryRow] = []
        row_idx = 0

        # Lines to ignore (technical noise, comments, clinical footers)
        ignore_substrings = [
            "strona ", "data wydruku", "pesel", "nr zlecenia", "pacjent:", "lekarz:",
            "metoda:", "metoda ", "analizator:", "komentarz:", "zatwierdził",
            "punkt pobrań", "zleceniodawca", "opis badania", "uwagi:", "normy:",
            "antagonistami", "witaminy k", "tel. ", "fax ", "instrukcja "
        ]

        # Regular expression for full or partial result line
        result_line_pattern = re.compile(
            r"^(?:(?P<name>[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż\(\)][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\(\)\-\/\.,%#\+]*?)\s+)?"
            r"(?P<val>[<>]?\s*\d+(?:[\.,]\d+)?|nieobecny|obecny|dodatni|ujemny|nieobecne|obecne|przejrzysty)\s*"
            r"(?P<unit>[A-Za-zµμ\%/0-9\^\-\#\*\+]+(?:\s+FEU)?)?\s*"
            r"(?P<ref>(?:[<>]\s*\d+(?:[\.,]\d+)?|\d+(?:[\.,]\d+)?\s*[\-\u2012\u2013\u2014\u2212]\s*\d+(?:[\.,]\d+)?))?\s*"
            r"(?P<flag>[HL\*])?$",
            re.IGNORECASE,
        )

        pending_name: Optional[str] = None

        for page_num, line in lines:
            line_str = line.strip()
            line_lower = line_str.lower()

            if any(sub in line_lower for sub in ignore_substrings):
                continue

            # Skip table header lines
            if "badanie" in line_lower and "wynik" in line_lower:
                continue

            # Check match
            m = result_line_pattern.match(line_str)

            if m:
                matched_name = m.group("name")
                matched_val = m.group("val")
                matched_unit = m.group("unit") or ""
                matched_ref = m.group("ref") or None
                matched_flag = m.group("flag") or None

                if matched_name and matched_name.strip():
                    name_str = matched_name.strip()
                    pending_name = None
                elif pending_name:
                    name_str = pending_name
                    pending_name = None
                else:
                    continue

                # Final validation: name must contain letters
                if not any(c.isalpha() for c in name_str):
                    continue

                rows.append(
                    RawLaboratoryRow(
                        report_row_index=row_idx,
                        raw_name=name_str,
                        raw_value=matched_val.strip(),
                        raw_unit=matched_unit.strip(),
                        raw_reference_text=matched_ref.strip() if matched_ref else None,
                        raw_flag=matched_flag.strip() if matched_flag else None,
                        collected_at=collected_at,
                        reported_at=reported_at,
                        laboratory_name=laboratory_name,
                    )
                )
                row_idx += 1
                continue

            # If line is a biomarker name or part of multiline name without values
            if len(line_str) < 60 and not any(c.isdigit() for c in line_str):
                clean_name = line_str.rstrip("/:").strip()
                if clean_name and not any(k in line_lower for k in ["badanie", "wynik", "zakres"]):
                    pending_name = clean_name

        return rows
