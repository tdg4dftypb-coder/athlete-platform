import pytest
from biomarkers.intelligence import (
    BiomarkerInsightRuleRegistry,
    BiomarkerInsightAnalyzer,
    GenericIncreasingRule,
    GenericDecreasingRule,
    GenericStableRule,
    GenericUnknownRule,
)
from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)


class StubRule:
    def supports(self, canonical_code: str) -> bool:
        return True

    def evaluate(self, trend: BiomarkerTrend) -> None:
        return None


def test_registry_returns_all_rules_in_correct_order():
    registry = BiomarkerInsightRuleRegistry()
    rules = registry.rules()

    from biomarkers.intelligence.ferritin_rule import FerritinRule
    from biomarkers.intelligence.crp_rule import CRPRule
    from biomarkers.intelligence.vitamin_d_rule import VitaminDRule

    # Find indexes of rules
    idx_ferritin = next(i for i, r in enumerate(rules) if isinstance(r, FerritinRule))
    idx_crp = next(i for i, r in enumerate(rules) if isinstance(r, CRPRule))
    idx_vitamin_d = next(i for i, r in enumerate(rules) if isinstance(r, VitaminDRule))
    idx_generic = next(i for i, r in enumerate(rules) if isinstance(r, (GenericIncreasingRule, GenericDecreasingRule, GenericStableRule, GenericUnknownRule)))

    # Specialist rules must be present and evaluated before any generic rules
    assert idx_ferritin < idx_generic
    assert idx_crp < idx_generic
    assert idx_vitamin_d < idx_generic

    # Sequence of specialist rules: Ferritin -> CRP -> Vitamin D
    assert idx_ferritin < idx_crp
    assert idx_crp < idx_vitamin_d


def test_registry_returns_immutable_collection():
    registry = BiomarkerInsightRuleRegistry()
    rules = registry.rules()

    assert isinstance(rules, tuple)
    # Check that it raises exception when attempting modification
    with pytest.raises(TypeError):
        rules[0] = StubRule()  # type: ignore


def test_analyzer_uses_registry_by_default():
    analyzer = BiomarkerInsightAnalyzer()
    
    # Verify that analyzer has loaded specialist rules and generic rules
    from biomarkers.intelligence.ferritin_rule import FerritinRule
    assert any(isinstance(r, FerritinRule) for r in analyzer._rules)
    assert any(isinstance(r, GenericIncreasingRule) for r in analyzer._rules)


def test_analyzer_supports_dependency_injection():
    # Pass a custom rules list, verify it is used instead of registry
    custom_rule = StubRule()
    analyzer = BiomarkerInsightAnalyzer(rules=[custom_rule])  # type: ignore






def test_analyzer_supports_dependency_injection():
    # Pass a custom rules list, verify it is used instead of registry
    custom_rule = StubRule()
    analyzer = BiomarkerInsightAnalyzer(rules=[custom_rule])  # type: ignore

    assert len(analyzer._rules) == 1
    assert analyzer._rules[0] is custom_rule
