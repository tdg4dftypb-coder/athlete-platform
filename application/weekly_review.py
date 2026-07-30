from athlete.memory.models import DateRange
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.trends import TrendEngine
from athlete.review.models import WeeklyTrainingReview
from athlete.review.weekly import WeeklyReviewService


class WeeklyReviewWorkflow:
    """Builds a weekly review from a supplied athlete-memory period."""

    def __init__(
        self,
        reader: AthleteMemoryReader,
        trend_engine: TrendEngine,
        pattern_detector: PatternDetector,
        review_service: WeeklyReviewService,
    ) -> None:

        self.reader = reader
        self.trend_engine = trend_engine
        self.pattern_detector = pattern_detector
        self.review_service = review_service

    def run(
        self,
        period: DateRange,
    ) -> WeeklyTrainingReview:

        snapshot = self.reader.read(period)
        trends = self.trend_engine.analyze(snapshot)
        patterns = self.pattern_detector.analyze(snapshot)

        return self.review_service.build(trends, patterns)
