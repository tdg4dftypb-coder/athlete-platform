import pytest
from typing import Dict, Any

from biomarkers.intelligence import (
    RegistryConsistencyError,
    RegistryConsistencyValidator,
    validate_default_registry_consistency,
)


class StubAudit:
    def __init__(self, errors_list: list[str], warnings_list: list[str]) -> None:
        self.errors_list = errors_list
        self.warnings_list = warnings_list

    def run(self) -> Dict[str, Any]:
        return {
            "errors": self.errors_list,
            "warnings": self.warnings_list,
            "summary": {
                "total_biomarkers": 1,
                "total_rules": 5,
                "is_consistent": len(self.code_errors()) == 0,
            },
        }

    def code_errors(self) -> list[str]:
        return self.errors_list


def test_validator_with_no_errors_returns_report() -> None:
    # 0 errors, 1 warning
    audit = StubAudit(errors_list=[], warnings_list=["Some warning"])
    validator = RegistryConsistencyValidator(audit)  # type: ignore

    report = validator.validate()
    assert report["errors"] == []
    assert report["warnings"] == ["Some warning"]
    assert report["summary"]["is_consistent"] is True


def test_validator_with_errors_raises_custom_exception() -> None:
    # 2 errors, 0 warnings
    audit = StubAudit(errors_list=["Error 1", "Error 2"], warnings_list=[])
    validator = RegistryConsistencyValidator(audit)  # type: ignore

    with pytest.raises(RegistryConsistencyError) as exc_info:
        validator.validate()

    assert str(exc_info.value) == "Biomarker registry consistency validation failed with 2 errors."


def test_production_default_validation_pipeline_passes() -> None:
    # Verify that the production factory validates without raising errors
    report = validate_default_registry_consistency()
    
    assert report["errors"] == []
    assert report["summary"]["is_consistent"] is True
    assert isinstance(report["warnings"], list)
    assert len(report["warnings"]) > 0  # Should have warnings about generic fallbacks
