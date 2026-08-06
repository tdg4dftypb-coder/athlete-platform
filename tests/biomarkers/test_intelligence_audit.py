import pytest
from typing import Tuple

from biomarkers.models import BiomarkerDefinition, BiomarkerValueType, BiomarkerCategory
from biomarkers.registry import BiomarkerRegistry
from biomarkers.intelligence.rules import (
    BiomarkerInsightRule,
    GenericIncreasingRule,
    GenericDecreasingRule,
    GenericStableRule,
    GenericUnknownRule,
)
from biomarkers.intelligence.registry import BiomarkerInsightRuleRegistry
from biomarkers.intelligence.audit import RegistryConsistencyAudit


class StubRule(BiomarkerInsightRule):
    def __init__(self, code: str) -> None:
        self.code = code

    def supports(self, canonical_code: str) -> bool:
        return canonical_code == self.code

    def evaluate(self, trend: any) -> any:
        return None


class FakeRuleRegistry(BiomarkerInsightRuleRegistry):
    def __init__(self, rules_tuple: Tuple[BiomarkerInsightRule, ...]) -> None:
        self._rules = rules_tuple

    def rules(self) -> Tuple[BiomarkerInsightRule, ...]:
        return self._rules


def make_definition(code: str) -> BiomarkerDefinition:
    return BiomarkerDefinition(
        canonical_code=code,
        canonical_name=code.capitalize(),
        category=BiomarkerCategory.OTHER,
        default_unit="ng/mL",
        accepted_aliases=(code.capitalize(),),
        accepted_units=("ng/mL",),
        value_type=BiomarkerValueType.NUMERIC,
    )


def test_audit_full_consistency() -> None:
    # 1. Prepare registry with ferritin
    biomarker_registry = BiomarkerRegistry()
    biomarker_registry.register(make_definition("ferritin"))

    # 2. Rule registry with StubRule("ferritin") and Generics
    rule_registry = FakeRuleRegistry((
        StubRule("ferritin"),
        GenericIncreasingRule(),
        GenericDecreasingRule(),
        GenericStableRule(),
        GenericUnknownRule(),
    ))

    # Run audit
    audit = RegistryConsistencyAudit(biomarker_registry, rule_registry)
    result = audit.run()

    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0
    assert result["summary"]["total_biomarkers"] == 1
    assert result["summary"]["total_rules"] == 5
    assert result["summary"]["specialist_rules"] == 1
    assert result["summary"]["generic_rules"] == 4
    assert result["summary"]["is_consistent"] is True


def test_audit_missing_biomarker_for_rule_returns_error() -> None:
    # Rule registry has rule for glucose, but Biomarker Registry is empty
    biomarker_registry = BiomarkerRegistry()

    rule_registry = FakeRuleRegistry((
        StubRule("glucose"),
        GenericIncreasingRule(),
    ))

    audit = RegistryConsistencyAudit(biomarker_registry, rule_registry)
    result = audit.run()

    assert len(result["errors"]) == 1
    assert "StubRule" in result["errors"][0]
    assert len(result["warnings"]) == 0
    assert result["summary"]["is_consistent"] is False


def test_audit_missing_rule_for_biomarker_returns_warning() -> None:
    # Registry has hemoglobin, but rules only contain generics
    biomarker_registry = BiomarkerRegistry()
    biomarker_registry.register(make_definition("hemoglobin"))

    rule_registry = FakeRuleRegistry((
        GenericIncreasingRule(),
        GenericDecreasingRule(),
    ))

    audit = RegistryConsistencyAudit(biomarker_registry, rule_registry)
    result = audit.run()

    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 1
    assert "hemoglobin" in result["warnings"][0]
    assert result["summary"]["is_consistent"] is True


def test_audit_empty_registries() -> None:
    biomarker_registry = BiomarkerRegistry()
    rule_registry = FakeRuleRegistry(())

    audit = RegistryConsistencyAudit(biomarker_registry, rule_registry)
    result = audit.run()

    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0
    assert result["summary"]["total_biomarkers"] == 0
    assert result["summary"]["total_rules"] == 0
    assert result["summary"]["specialist_rules"] == 0
    assert result["summary"]["generic_rules"] == 0
    assert result["summary"]["is_consistent"] is True
