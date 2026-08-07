from enum import Enum
from typing import Any

from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from decision.history_v2 import DecisionAuditRecord
from decision.policy_v2 import DecisionPolicyResult, DecisionPolicySignal
from decision.recommendation_plan import (
    DecisionExplanation,
    DecisionExplanationItem,
    DecisionRecommendation,
    RecommendationPlan,
)


def _serialize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Enum):
        return v.value
    return v


class DecisionAuditRecordSerializer:
    """Stateless serializer converting DecisionAuditRecord into a JSON-safe dict.

    Does not perform any business logic, decision execution, or infrastructure access.
    """

    def serialize(self, record: DecisionAuditRecord) -> dict[str, object]:
        if not isinstance(record, DecisionAuditRecord):
            raise TypeError("record must be DecisionAuditRecord")

        return {
            "decision_id": record.decision_id,
            "recorded_at": record.recorded_at.isoformat(),
            "context": self._serialize_context(record.context),
            "policy_result": self._serialize_policy_result(record.policy_result),
            "recommendation_plan": self._serialize_recommendation_plan(record.recommendation_plan),
        }

    def _serialize_context(self, context: AthleteDecisionContext) -> dict[str, object]:
        return {
            "generated_at": context.generated_at.isoformat(),
            "recovery": self._serialize_recovery_context(context.recovery),
            "training": self._serialize_training_context(context.training),
            "biomarkers": self._serialize_biomarkers_context(context.biomarkers),
            "performance": self._serialize_performance_context(context.performance),
        }

    def _serialize_recovery_context(self, recovery: RecoveryDecisionContext) -> dict[str, object]:
        return {
            "status": recovery.status.value,
            "recovery_score": recovery.recovery_score,
            "recovery_status": recovery.recovery_status,
            "hrv_status": recovery.hrv_status,
            "resting_heart_rate_status": recovery.resting_heart_rate_status,
            "sleep_status": recovery.sleep_status,
            "generated_at": recovery.generated_at.isoformat() if recovery.generated_at else None,
        }

    def _serialize_training_context(self, training: TrainingDecisionContext) -> dict[str, object]:
        return {
            "status": training.status.value,
            "planned_session_type": training.planned_session_type,
            "planned_duration_minutes": training.planned_duration_minutes,
            "planned_intensity": training.planned_intensity,
            "recent_training_load": training.recent_training_load,
            "fatigue_status": training.fatigue_status,
            "generated_at": training.generated_at.isoformat() if training.generated_at else None,
        }

    def _serialize_biomarkers_context(self, biomarkers: BiomarkerDecisionContext) -> dict[str, object]:
        return {
            "status": biomarkers.status.value,
            "attention_count": biomarkers.attention_count,
            "critical_count": biomarkers.critical_count,
            "signals": [self._serialize_biomarker_signal(s) for s in biomarkers.signals],
            "generated_at": biomarkers.generated_at.isoformat() if biomarkers.generated_at else None,
        }

    def _serialize_biomarker_signal(self, signal: BiomarkerDecisionSignal) -> dict[str, object]:
        return {
            "canonical_code": signal.canonical_code,
            "interpretation": signal.interpretation,
            "confidence": signal.confidence,
            "summary": signal.summary,
        }

    def _serialize_performance_context(self, performance: PerformanceDecisionContext) -> dict[str, object]:
        return {
            "status": performance.status.value,
            "latest_test_id": performance.latest_test_id,
            "latest_test_type": performance.latest_test_type,
            "performed_at": performance.performed_at.isoformat() if performance.performed_at else None,
            "lt1": self._serialize_threshold_snapshot(performance.lt1) if performance.lt1 else None,
            "lt2": self._serialize_threshold_snapshot(performance.lt2) if performance.lt2 else None,
        }

    def _serialize_threshold_snapshot(self, snapshot: PerformanceThresholdSnapshot) -> dict[str, object]:
        return {
            "name": snapshot.name,
            "status": snapshot.status,
            "power_watts": snapshot.power_watts,
            "speed_kph": snapshot.speed_kph,
            "heart_rate_bpm": snapshot.heart_rate_bpm,
            "lactate_mmol_l": snapshot.lactate_mmol_l,
            "confidence": snapshot.confidence,
            "method": snapshot.method,
        }

    def _serialize_policy_result(self, result: DecisionPolicyResult) -> dict[str, object]:
        return {
            "generated_at": result.generated_at.isoformat(),
            "action": result.action.value,
            "severity": result.severity.value,
            "signals": [self._serialize_policy_signal(s) for s in result.signals],
            "confidence": result.confidence,
            "policy_version": result.policy_version,
        }

    def _serialize_policy_signal(self, signal: DecisionPolicySignal) -> dict[str, object]:
        return {
            "code": signal.code,
            "source": signal.source,
            "severity": signal.severity.value,
            "summary": signal.summary,
        }

    def _serialize_recommendation_plan(self, plan: RecommendationPlan) -> dict[str, object]:
        return {
            "generated_at": plan.generated_at.isoformat(),
            "action": plan.action.value,
            "severity": plan.severity.value,
            "confidence": plan.confidence,
            "policy_version": plan.policy_version,
            "recommendations": [self._serialize_recommendation(r) for r in plan.recommendations],
            "explanation": self._serialize_explanation(plan.explanation),
        }

    def _serialize_recommendation(self, rec: DecisionRecommendation) -> dict[str, object]:
        return {
            "code": rec.code,
            "category": rec.category.value,
            "priority": rec.priority.value,
            "title": rec.title,
            "description": rec.description,
            "source_signal_codes": list(rec.source_signal_codes),
        }

    def _serialize_explanation(self, explanation: DecisionExplanation) -> dict[str, object]:
        return {
            "headline": explanation.headline,
            "summary": explanation.summary,
            "items": [self._serialize_explanation_item(item) for item in explanation.items],
        }

    def _serialize_explanation_item(self, item: DecisionExplanationItem) -> dict[str, object]:
        return {
            "signal_code": item.signal_code,
            "source": item.source,
            "severity": item.severity.value,
            "summary": item.summary,
        }
