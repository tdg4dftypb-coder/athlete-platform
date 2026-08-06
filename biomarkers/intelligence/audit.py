from typing import Any, List, Dict
from biomarkers.registry import BiomarkerRegistry
from biomarkers.intelligence.registry import BiomarkerInsightRuleRegistry
from biomarkers.intelligence.rules import (
    GenericIncreasingRule,
    GenericDecreasingRule,
    GenericStableRule,
    GenericUnknownRule,
)


class RegistryConsistencyAudit:
    """
    Audit utility to verify alignment and consistency between the Biomarker Registry
    and the Medical Intelligence Rules.
    """

    def __init__(
        self,
        biomarker_registry: BiomarkerRegistry,
        rule_registry: BiomarkerInsightRuleRegistry,
    ) -> None:
        self._biomarker_registry = biomarker_registry
        self._rule_registry = rule_registry

    def run(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        all_definitions = self._biomarker_registry.list_all()
        all_rules = self._rule_registry.rules()

        # Identify generic vs specialist rules
        generic_types = (
            GenericIncreasingRule,
            GenericDecreasingRule,
            GenericStableRule,
            GenericUnknownRule,
        )
        specialist_rules = [r for r in all_rules if not isinstance(r, generic_types)]

        # Audit 1: Check that every specialist rule has a matching biomarker in registry
        for rule in specialist_rules:
            matched_codes = [
                defn.canonical_code
                for defn in all_definitions
                if rule.supports(defn.canonical_code)
            ]
            if not matched_codes:
                rule_name = rule.__class__.__name__
                errors.append(
                    f"Specialist rule '{rule_name}' does not support any active biomarker in the registry."
                )

        # Audit 2: Check that every biomarker in registry has a specialist rule
        for defn in all_definitions:
            supported_by_specialist = any(
                rule.supports(defn.canonical_code) for rule in specialist_rules
            )
            if not supported_by_specialist:
                warnings.append(
                    f"Biomarker '{defn.canonical_code}' does not have a registered specialist rule (falls back to generic rules)."
                )

        is_consistent = len(errors) == 0

        return {
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "total_biomarkers": len(all_definitions),
                "total_rules": len(all_rules),
                "specialist_rules": len(specialist_rules),
                "generic_rules": len(all_rules) - len(specialist_rules),
                "is_consistent": is_consistent,
            },
        }
