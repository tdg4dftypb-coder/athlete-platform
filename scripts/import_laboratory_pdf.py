#!/usr/bin/env python3
"""
CLI Utility for Importing Text PDF Laboratory Reports into Biomarkers Database.
Enforces privacy boundaries: zero raw health values or patient data printed to stdout/stderr.
"""

import argparse
from pathlib import Path
import sys

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.extraction.errors import LaboratoryExtractionError
from biomarkers.use_cases import ImportLaboratoryPdfUseCase, PdfImportSummary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Privacy-safe CLI tool for importing digital PDF laboratory reports."
    )
    parser.add_argument("pdf_path", type=str, help="Path to PDF laboratory report file.")
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/database/biomarkers.duckdb",
        help="Path to DuckDB database file (default: data/database/biomarkers.duckdb).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extraction, parsing, and normalization without saving records to database.",
    )
    parser.add_argument(
        "--show-summary",
        action="store_true",
        help="Print detailed privacy-safe summary metrics after import.",
    )
    parser.add_argument(
        "--lab-name",
        type=str,
        default=None,
        help="Optional laboratory name fallback/override.",
    )

    args = parser.parse_args()

    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists() or not pdf_file.is_file():
        print(f"Error: Specified PDF file does not exist or is not a file.", file=sys.stderr)
        return 1

    try:
        content = pdf_file.read_bytes()
    except Exception as err:
        print(f"Error reading PDF file content: {type(err).__name__}", file=sys.stderr)
        return 1

    # Initialize Application Context
    try:
        ctx = BiomarkersApplicationContext(db_path=args.db_path)
        use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service)
        summary: PdfImportSummary = use_case.execute(
            pdf_content=content,
            laboratory_name_override=args.lab_name,
            dry_run=args.dry_run,
        )
    except LaboratoryExtractionError as err:
        print(f"Extraction Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Import Error: {type(err).__name__}", file=sys.stderr)
        return 1

    # Output Privacy-Safe Result Summary
    mode_str = "[DRY-RUN] " if summary.dry_run else ""
    if summary.status.value == "completed":
        print(f"{mode_str}Laboratory PDF import completed successfully.")
    elif summary.status.value == "partial":
        print(f"{mode_str}Laboratory PDF import completed with warnings/unresolved items.")
    else:
        print(f"{mode_str}Laboratory PDF import failed or blocked.")
        for warn in summary.warnings:
            print(f"  Warning: {warn}", file=sys.stderr)
        return 1

    if args.show_summary or summary.dry_run:
        resolved_cnt = len(summary.resolved_canonical_codes)
        print("--- Execution Summary ---")
        print(f"  Laboratory:             {summary.laboratory_name or 'Unknown'}")
        print(f"  Collection Date Found:  {'YES' if summary.collected_at_detected else 'NO'}")
        print(f"  Page Count:             {summary.page_count}")
        print(f"  Extracted Rows:         {summary.extracted_rows_count}")
        print(f"  Imported Observations:  {summary.imported_observations_count}")
        print(f"  Resolved Biomarkers:    {resolved_cnt}")
        print(f"  Unresolved Items:       {summary.unresolved_observations_count}")
        print(f"  Possible Duplicates:    {summary.possible_duplicates_count}")
        if summary.resolved_canonical_codes:
            print(f"  Recognized Codes:       [{', '.join(summary.resolved_canonical_codes)}]")
        if summary.unresolved_raw_names:
            print(f"  Unresolved Names:       [{', '.join(summary.unresolved_raw_names)}]")
        if summary.report_id:
            print(f"  Report ID:              {summary.report_id}")
        if summary.warnings:
            print("  Warnings:")
            for w in summary.warnings:
                print(f"    - {w}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
