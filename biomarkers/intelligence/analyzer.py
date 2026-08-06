from biomarkers.trends.models import BiomarkerTrend
from biomarkers.intelligence.models import BiomarkerInsight
from biomarkers.intelligence.rules import BiomarkerInsightRule
from biomarkers.intelligence.registry import BiomarkerInsightRuleRegistry


class BiomarkerInsightAnalyzer:
    """
    Orchestrator responsible for evaluating BiomarkerTrends against a list of registered rules
    to produce BiomarkerInsights.
    """

    def __init__(self, rules: list[BiomarkerInsightRule] | None = None) -> None:
        if rules is not None:
            self._rules = rules
        else:
            self._rules = list(BiomarkerInsightRuleRegistry().rules())

    def analyze(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        for rule in self._rules:
            if rule.supports(trend.canonical_code):
                return rule.evaluate(trend)
        raise LookupError(
            f"No registered intelligence rule supports biomarker '{trend.canonical_code}'."
        )

