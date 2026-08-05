"""
Parser Selection Factory for Laboratory PDF Text Reports.
Selects specialized parsers (e.g., AlabTextLaboratoryReportParser) when format signatures match,
falling back to generic TextLaboratoryReportParser.
"""

from typing import List

from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument
from biomarkers.ingestion import LaboratoryResultParser
from biomarkers.parsing.alab_report_parser import AlabTextLaboratoryReportParser
from biomarkers.parsing.text_report_parser import TextLaboratoryReportParser


def get_report_parser_for_document(document: ExtractedLaboratoryDocument) -> LaboratoryResultParser:
    """
    Selects the most specific parser capable of parsing the given document.
    """
    alab_parser = AlabTextLaboratoryReportParser()
    if alab_parser.can_parse(document):
        return alab_parser

    return TextLaboratoryReportParser()
