import pytest
from scripts.validate_biomarker_registry_consistency import main
from biomarkers.intelligence.validation import RegistryConsistencyError


def test_cli_success(capsys) -> None:
    # Stub function returning valid report
    def mock_validate() -> dict:
        return {"errors": [], "warnings": ["w1", "w2"], "summary": {}}

    code = main(validate_fn=mock_validate)
    assert code == 0

    captured = capsys.readouterr()
    assert "Biomarker registry consistency: PASS" in captured.out
    assert "Errors: 0" in captured.out
    assert "Warnings: 2" in captured.out


def test_cli_failure(capsys) -> None:
    # Stub function raising RegistryConsistencyError
    def mock_validate() -> dict:
        raise RegistryConsistencyError("Biomarker registry consistency validation failed with 3 errors.")

    code = main(validate_fn=mock_validate)
    assert code == 1

    captured = capsys.readouterr()
    assert "Biomarker registry consistency: FAIL" in captured.out
    assert "Errors: 3" in captured.out
    # Ensure there is no python traceback in output (it's handled cleanly by main)
    assert "Traceback" not in captured.out
    assert "RegistryConsistencyError" not in captured.out
