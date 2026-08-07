"""Performance Lab — public package API."""
from performance_lab.domain import (
    PerformanceTestType,
    PerformanceTestStatus,
    ExerciseModality,
    StageCompletionStatus,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceThreshold,
    PerformanceAssessment,
)
from performance_lab.input_models import (
    PerformanceStageInput,
    PerformanceTestSessionInput,
)
from performance_lab.builder import PerformanceTestSessionBuilder
from performance_lab.lactate_curve import (
    LactateCurvePoint,
    LactateCurve,
    LactateCurveBuilder,
)
from performance_lab.thresholds import (
    ThresholdDetectionStatus,
    DetectedThreshold,
    LactateThresholdAnalysis,
    LactateThresholdAnalyzer,
)
from performance_lab.history import (
    PerformanceHistoryEntry,
    PerformanceTestHistory,
    PerformanceTestHistoryBuilder,
)
from performance_lab.serialization import PerformanceTestHistorySerializer
from performance_lab.provider import (
    PerformanceTestSessionProviderError,
    PerformanceTestSessionProvider,
    EmptyPerformanceTestSessionProvider,
    PerformanceTestHistoryProviderError,
    PerformanceTestHistoryProvider,
    EmptyPerformanceTestHistoryProvider,
)

__all__ = [
    # Domain models
    "PerformanceTestType",
    "PerformanceTestStatus",
    "ExerciseModality",
    "StageCompletionStatus",
    "PerformanceStage",
    "PerformanceTestSession",
    "PerformanceThreshold",
    "PerformanceAssessment",
    # Input models
    "PerformanceStageInput",
    "PerformanceTestSessionInput",
    # Builder
    "PerformanceTestSessionBuilder",
    # Lactate curve
    "LactateCurvePoint",
    "LactateCurve",
    "LactateCurveBuilder",
    # Thresholds
    "ThresholdDetectionStatus",
    "DetectedThreshold",
    "LactateThresholdAnalysis",
    "LactateThresholdAnalyzer",
    # History
    "PerformanceHistoryEntry",
    "PerformanceTestHistory",
    "PerformanceTestHistoryBuilder",
    # Serialization
    "PerformanceTestHistorySerializer",
    # Provider
    "PerformanceTestSessionProviderError",
    "PerformanceTestSessionProvider",
    "EmptyPerformanceTestSessionProvider",
    "PerformanceTestHistoryProviderError",
    "PerformanceTestHistoryProvider",
    "EmptyPerformanceTestHistoryProvider",
]
