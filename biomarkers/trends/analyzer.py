from biomarkers.history import BiomarkerHistory
from biomarkers.trends.models import BiomarkerTrend
from biomarkers.trends.builder import BiomarkerTrendBuilder
from biomarkers.trends.classifier import TrendClassifier


class BiomarkerTrendAnalyzer:
    """
    Orchestrator for the trend engine pipeline:
    BiomarkerHistory -> BiomarkerTrendBuilder -> TrendClassifier -> BiomarkerTrend
    """

    def __init__(
        self,
        builder: BiomarkerTrendBuilder | None = None,
        classifier: TrendClassifier | None = None,
    ) -> None:
        self.builder = builder or BiomarkerTrendBuilder()
        self.classifier = classifier or TrendClassifier()

    def analyze(self, history: BiomarkerHistory) -> BiomarkerTrend:
        trend = self.builder.build_trend(history)
        return self.classifier.classify(trend)
