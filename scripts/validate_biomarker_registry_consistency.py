import re
import sys
from biomarkers.intelligence.validation import (
    validate_default_registry_consistency,
    RegistryConsistencyError,
)


def main(validate_fn=None) -> int:
    """
    Main entry point for the Biomarker Registry consistency validation CLI.
    """
    if validate_fn is None:
        validate_fn = validate_default_registry_consistency

    try:
        report = validate_fn()
        warnings_count = len(report.get("warnings", []))
        print("Biomarker registry consistency: PASS")
        print("Errors: 0")
        print(f"Warnings: {warnings_count}")
        return 0
    except RegistryConsistencyError as e:
        msg = str(e)
        match = re.search(r"failed with (\d+) errors", msg)
        err_count = int(match.group(1)) if match else 1

        print("Biomarker registry consistency: FAIL")
        print(f"Errors: {err_count}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
