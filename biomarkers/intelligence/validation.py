from biomarkers.intelligence.audit import RegistryConsistencyAudit


class RegistryConsistencyError(Exception):
    """
    Exception raised when biomarker registry consistency validation fails.
    """
    pass


class RegistryConsistencyValidator:
    """
    Validator that acts as a quality gate using a RegistryConsistencyAudit report.
    """

    def __init__(self, audit: RegistryConsistencyAudit) -> None:
        self._audit = audit

    def validate(self) -> dict:
        report = self._audit.run()
        errors = report.get("errors", [])
        if errors:
            raise RegistryConsistencyError(
                f"Biomarker registry consistency validation failed with {len(errors)} errors."
            )
        return report


def validate_default_registry_consistency() -> dict:
    """
    Production factory function that builds default registries, runs audit
    and validates consistency. Used as a single entry point for validation.
    """
    from biomarkers.registry import create_default_biomarker_registry
    from biomarkers.intelligence.registry import BiomarkerInsightRuleRegistry

    biomarker_registry = create_default_biomarker_registry()
    rule_registry = BiomarkerInsightRuleRegistry()
    audit = RegistryConsistencyAudit(biomarker_registry, rule_registry)
    validator = RegistryConsistencyValidator(audit)
    return validator.validate()
