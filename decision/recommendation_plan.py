from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from decision.policy_v2 import DecisionAction, DecisionPolicyResult, DecisionSeverity


class RecommendationCategory(str, Enum):
    TRAINING = "training"
    RECOVERY = "recovery"
    LABORATORY = "laboratory"
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"


class RecommendationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DecisionRecommendation:
    code: str
    category: RecommendationCategory
    priority: RecommendationPriority
    title: str
    description: str
    source_signal_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be non-empty string")
        if not isinstance(self.category, RecommendationCategory):
            raise TypeError("category must be RecommendationCategory")
        if not isinstance(self.priority, RecommendationPriority):
            raise TypeError("priority must be RecommendationPriority")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be non-empty string")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be non-empty string")
        if not isinstance(self.source_signal_codes, tuple):
            raise TypeError("source_signal_codes must be tuple")
        if len(self.source_signal_codes) == 0:
            raise ValueError("source_signal_codes cannot be empty")

        seen_codes: set[str] = set()
        for src_code in self.source_signal_codes:
            if not isinstance(src_code, str) or not src_code.strip():
                raise ValueError("source_signal_codes items must be non-empty string")
            if src_code in seen_codes:
                raise ValueError(f"Duplicate source_signal_code: {src_code}")
            seen_codes.add(src_code)


@dataclass(frozen=True)
class DecisionExplanationItem:
    signal_code: str
    source: str
    severity: DecisionSeverity
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.signal_code, str) or not self.signal_code.strip():
            raise ValueError("signal_code must be non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be non-empty string")
        if not isinstance(self.severity, DecisionSeverity):
            raise TypeError("severity must be DecisionSeverity")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be non-empty string")


@dataclass(frozen=True)
class DecisionExplanation:
    headline: str
    summary: str
    items: tuple[DecisionExplanationItem, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.headline, str) or not self.headline.strip():
            raise ValueError("headline must be non-empty string")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be non-empty string")
        if not isinstance(self.items, tuple):
            raise TypeError("items must be tuple")
        if len(self.items) == 0:
            raise ValueError("items cannot be empty")

        seen_codes: set[str] = set()
        for item in self.items:
            if not isinstance(item, DecisionExplanationItem):
                raise TypeError("items elements must be DecisionExplanationItem")
            if item.signal_code in seen_codes:
                raise ValueError(f"Duplicate item signal_code: {item.signal_code}")
            seen_codes.add(item.signal_code)


@dataclass(frozen=True)
class RecommendationPlan:
    generated_at: datetime
    action: DecisionAction
    severity: DecisionSeverity
    confidence: float
    policy_version: str
    recommendations: tuple[DecisionRecommendation, ...]
    explanation: DecisionExplanation

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be datetime")
        if not isinstance(self.action, DecisionAction):
            raise TypeError("action must be DecisionAction")
        if not isinstance(self.severity, DecisionSeverity):
            raise TypeError("severity must be DecisionSeverity")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty string")
        if not isinstance(self.recommendations, tuple):
            raise TypeError("recommendations must be tuple")
        if len(self.recommendations) == 0:
            raise ValueError("recommendations cannot be empty")
        if not isinstance(self.explanation, DecisionExplanation):
            raise TypeError("explanation must be DecisionExplanation")

        seen_codes: set[str] = set()
        for rec in self.recommendations:
            if not isinstance(rec, DecisionRecommendation):
                raise TypeError("recommendations items must be DecisionRecommendation")
            if rec.code in seen_codes:
                raise ValueError(f"Duplicate recommendation code: {rec.code}")
            seen_codes.add(rec.code)


class RecommendationPlanBuilder:
    """Stateless builder converting DecisionPolicyResult into RecommendationPlan and DecisionExplanation."""

    _SEVERITY_PRIORITY_MAP: dict[DecisionSeverity, RecommendationPriority] = {
        DecisionSeverity.LOW: RecommendationPriority.LOW,
        DecisionSeverity.MEDIUM: RecommendationPriority.MEDIUM,
        DecisionSeverity.HIGH: RecommendationPriority.HIGH,
        DecisionSeverity.CRITICAL: RecommendationPriority.CRITICAL,
    }

    _HEADLINE_MAP: dict[DecisionAction, str] = {
        DecisionAction.PROCEED: "Training can proceed",
        DecisionAction.REDUCE: "Training load should be reduced",
        DecisionAction.REPLACE_WITH_RECOVERY: "Recovery should replace the planned session",
        DecisionAction.REST: "Rest is recommended",
        DecisionAction.REVIEW: "Decision signals require review",
    }

    _SUMMARY_MAP: dict[DecisionAction, str] = {
        DecisionAction.PROCEED: "The available signals support proceeding with the planned session.",
        DecisionAction.REDUCE: "The available signals support training only with reduced load.",
        DecisionAction.REPLACE_WITH_RECOVERY: "The available signals support replacing the planned session with recovery.",
        DecisionAction.REST: "The available signals support avoiding the planned session and prioritizing rest.",
        DecisionAction.REVIEW: "The available signals require review before a training decision is finalized.",
    }

    def build(self, result: DecisionPolicyResult) -> RecommendationPlan:
        if not isinstance(result, DecisionPolicyResult):
            raise TypeError("result must be DecisionPolicyResult")

        main_rec = self._build_main_recommendation(result)

        # Collect additional recommendations based strictly on specific signal codes
        signal_codes = [s.code for s in result.signals]
        additional_recs: list[DecisionRecommendation] = []

        # 2. Laboratory group
        if "biomarker_critical" in signal_codes:
            additional_recs.append(
                DecisionRecommendation(
                    code="review_critical_laboratory_signals",
                    category=RecommendationCategory.LABORATORY,
                    priority=RecommendationPriority.CRITICAL,
                    title="Review critical laboratory signals",
                    description="Review critical laboratory findings before returning to normal training.",
                    source_signal_codes=("biomarker_critical",),
                )
            )
        elif "biomarker_attention" in signal_codes:
            additional_recs.append(
                DecisionRecommendation(
                    code="review_laboratory_signals",
                    category=RecommendationCategory.LABORATORY,
                    priority=RecommendationPriority.HIGH,
                    title="Review laboratory signals",
                    description="Review laboratory findings that require attention.",
                    source_signal_codes=("biomarker_attention",),
                )
            )

        # 3. Data Quality group
        if "context_all_unavailable" in signal_codes:
            additional_recs.append(
                DecisionRecommendation(
                    code="restore_decision_data",
                    category=RecommendationCategory.DATA_QUALITY,
                    priority=RecommendationPriority.HIGH,
                    title="Restore decision data",
                    description="Restore unavailable decision data sources before making a training decision.",
                    source_signal_codes=("context_all_unavailable",),
                )
            )
        if "context_stale" in signal_codes:
            additional_recs.append(
                DecisionRecommendation(
                    code="refresh_stale_data",
                    category=RecommendationCategory.DATA_QUALITY,
                    priority=RecommendationPriority.MEDIUM,
                    title="Refresh stale data",
                    description="Refresh outdated source data before relying on this decision.",
                    source_signal_codes=("context_stale",),
                )
            )

        # 4. Performance group
        if "performance_threshold_invalid" in signal_codes:
            additional_recs.append(
                DecisionRecommendation(
                    code="review_performance_analysis",
                    category=RecommendationCategory.PERFORMANCE,
                    priority=RecommendationPriority.MEDIUM,
                    title="Review performance analysis",
                    description="Review the latest performance threshold analysis before using it for training decisions.",
                    source_signal_codes=("performance_threshold_invalid",),
                )
            )

        all_recommendations = (main_rec, *additional_recs)

        # Build Explanation
        explanation_items = tuple(
            DecisionExplanationItem(
                signal_code=s.code,
                source=s.source,
                severity=s.severity,
                summary=s.summary,
            )
            for s in result.signals
        )

        explanation = DecisionExplanation(
            headline=self._HEADLINE_MAP[result.action],
            summary=self._SUMMARY_MAP[result.action],
            items=explanation_items,
        )

        return RecommendationPlan(
            generated_at=result.generated_at,
            action=result.action,
            severity=result.severity,
            confidence=result.confidence,
            policy_version=result.policy_version,
            recommendations=all_recommendations,
            explanation=explanation,
        )

    def _build_main_recommendation(self, result: DecisionPolicyResult) -> DecisionRecommendation:
        priority = self._SEVERITY_PRIORITY_MAP[result.severity]
        signal_codes = tuple(s.code for s in result.signals)

        if result.action == DecisionAction.PROCEED:
            return DecisionRecommendation(
                code="proceed_as_planned",
                category=RecommendationCategory.TRAINING,
                priority=priority,
                title="Proceed as planned",
                description="Current decision signals support the planned training session.",
                source_signal_codes=signal_codes,
            )
        elif result.action == DecisionAction.REDUCE:
            return DecisionRecommendation(
                code="reduce_training_load",
                category=RecommendationCategory.TRAINING,
                priority=priority,
                title="Reduce training load",
                description="Reduce the duration or intensity of the planned training session.",
                source_signal_codes=signal_codes,
            )
        elif result.action == DecisionAction.REPLACE_WITH_RECOVERY:
            return DecisionRecommendation(
                code="replace_with_recovery",
                category=RecommendationCategory.RECOVERY,
                priority=priority,
                title="Replace with recovery",
                description="Replace the planned session with low-intensity recovery activity.",
                source_signal_codes=signal_codes,
            )
        elif result.action == DecisionAction.REST:
            return DecisionRecommendation(
                code="prioritize_rest",
                category=RecommendationCategory.RECOVERY,
                priority=priority,
                title="Prioritize rest",
                description="Do not perform the planned training session and prioritize recovery.",
                source_signal_codes=signal_codes,
            )
        else:  # REVIEW
            return DecisionRecommendation(
                code="review_before_training",
                category=RecommendationCategory.DATA_QUALITY,
                priority=priority,
                title="Review before training",
                description="Review the available decision signals before performing the planned session.",
                source_signal_codes=signal_codes,
            )
