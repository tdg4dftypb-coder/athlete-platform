from datetime import datetime, timezone
import json
from typing import Any, Dict

from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from decision.history_v2 import DecisionAuditRecord, DecisionAuditRecordBuilder
from decision.policy_v2 import (
    DecisionAction,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionSeverity,
)
from decision.recommendation_plan import (
    DecisionExplanation,
    DecisionExplanationItem,
    DecisionRecommendation,
    RecommendationCategory,
    RecommendationPlan,
    RecommendationPriority,
)
from decision.repository import DecisionAuditRecordDataError
from decision.serialization_v2 import DecisionAuditRecordSerializer


class DecisionAuditRecordCodec:
    """Canonical JSON encoder and strict decoder for DecisionAuditRecord instances."""

    def __init__(
        self,
        serializer: DecisionAuditRecordSerializer | None = None,
        builder: DecisionAuditRecordBuilder | None = None,
    ) -> None:
        self._serializer = serializer or DecisionAuditRecordSerializer()
        self._builder = builder or DecisionAuditRecordBuilder()

    def encode(self, record: DecisionAuditRecord) -> str:
        if not isinstance(record, DecisionAuditRecord):
            raise TypeError("record must be DecisionAuditRecord")

        wire_dict = self._serializer.serialize(record)
        return json.dumps(wire_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def decode(self, payload_json: str) -> DecisionAuditRecord:
        if not isinstance(payload_json, str) or not payload_json.strip():
            raise DecisionAuditRecordDataError("payload_json must be a non-empty string")

        try:
            data = json.loads(payload_json)
        except Exception as err:
            raise DecisionAuditRecordDataError("Invalid JSON payload") from err

        if not isinstance(data, dict):
            raise DecisionAuditRecordDataError("Payload root must be an object")

        try:
            decision_id = data["decision_id"]
            recorded_at = self._parse_iso_datetime(data["recorded_at"])

            # 1. Context
            raw_ctx = data["context"]
            gen_at = self._parse_iso_datetime(raw_ctx["generated_at"])

            rec_ctx = self._decode_recovery(raw_ctx["recovery"])
            tr_ctx = self._decode_training(raw_ctx["training"])
            bio_ctx = self._decode_biomarkers(raw_ctx["biomarkers"])
            perf_ctx = self._decode_performance(raw_ctx["performance"])

            context = AthleteDecisionContext(
                generated_at=gen_at,
                recovery=rec_ctx,
                training=tr_ctx,
                biomarkers=bio_ctx,
                performance=perf_ctx,
            )

            # 2. Policy Result
            raw_pol = data["policy_result"]
            pol_gen_at = self._parse_iso_datetime(raw_pol["generated_at"])
            pol_signals = tuple(
                DecisionPolicySignal(
                    code=sig["code"],
                    source=sig["source"],
                    severity=DecisionSeverity(sig["severity"]),
                    summary=sig["summary"],
                )
                for sig in raw_pol["signals"]
            )

            policy_result = DecisionPolicyResult(
                generated_at=pol_gen_at,
                action=DecisionAction(raw_pol["action"]),
                severity=DecisionSeverity(raw_pol["severity"]),
                signals=pol_signals,
                confidence=float(raw_pol["confidence"]),
                policy_version=str(raw_pol["policy_version"]),
            )

            # 3. Recommendation Plan
            raw_plan = data["recommendation_plan"]
            plan_gen_at = self._parse_iso_datetime(raw_plan["generated_at"])
            recs = tuple(
                DecisionRecommendation(
                    code=rec["code"],
                    category=RecommendationCategory(rec["category"]),
                    priority=RecommendationPriority(rec["priority"]),
                    title=rec["title"],
                    description=rec["description"],
                    source_signal_codes=tuple(rec["source_signal_codes"]),
                )
                for rec in raw_plan["recommendations"]
            )

            raw_exp = raw_plan["explanation"]
            exp_items = tuple(
                DecisionExplanationItem(
                    signal_code=item["signal_code"],
                    source=item["source"],
                    severity=DecisionSeverity(item["severity"]),
                    summary=item["summary"],
                )
                for item in raw_exp["items"]
            )

            explanation = DecisionExplanation(
                headline=raw_exp["headline"],
                summary=raw_exp["summary"],
                items=exp_items,
            )

            recommendation_plan = RecommendationPlan(
                generated_at=plan_gen_at,
                action=DecisionAction(raw_plan["action"]),
                severity=DecisionSeverity(raw_plan["severity"]),
                confidence=float(raw_plan["confidence"]),
                policy_version=str(raw_plan["policy_version"]),
                recommendations=recs,
                explanation=explanation,
            )

            # Strict builder validation
            return self._builder.build(
                decision_id=decision_id,
                recorded_at=recorded_at,
                context=context,
                policy_result=policy_result,
                recommendation_plan=recommendation_plan,
            )
        except Exception as err:
            if isinstance(err, DecisionAuditRecordDataError):
                raise
            raise DecisionAuditRecordDataError("Corrupted or inconsistent DecisionAuditRecord payload") from err

    def _parse_iso_datetime(self, val: Any) -> datetime:
        if not isinstance(val, str):
            raise DecisionAuditRecordDataError("datetime must be ISO string")
        try:
            dt = datetime.fromisoformat(val)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception as err:
            raise DecisionAuditRecordDataError("Invalid ISO datetime format") from err

    def _decode_recovery(self, d: Dict[str, Any]) -> RecoveryDecisionContext:
        gen_at = self._parse_iso_datetime(d["generated_at"]) if d.get("generated_at") else None
        return RecoveryDecisionContext(
            status=ContextDataStatus(d["status"]),
            recovery_score=float(d["recovery_score"]) if d.get("recovery_score") is not None else None,
            recovery_status=d.get("recovery_status"),
            hrv_status=d.get("hrv_status"),
            resting_heart_rate_status=d.get("resting_heart_rate_status"),
            sleep_status=d.get("sleep_status"),
            generated_at=gen_at,
        )

    def _decode_training(self, d: Dict[str, Any]) -> TrainingDecisionContext:
        gen_at = self._parse_iso_datetime(d["generated_at"]) if d.get("generated_at") else None
        return TrainingDecisionContext(
            status=ContextDataStatus(d["status"]),
            planned_session_type=d.get("planned_session_type"),
            planned_duration_minutes=int(d["planned_duration_minutes"]) if d.get("planned_duration_minutes") is not None else None,
            planned_intensity=d.get("planned_intensity"),
            recent_training_load=float(d["recent_training_load"]) if d.get("recent_training_load") is not None else None,
            fatigue_status=d.get("fatigue_status"),
            generated_at=gen_at,
            plan_id=d.get("plan_id"),
            planned_session_id=d.get("planned_session_id"),
        )

    def _decode_biomarkers(self, d: Dict[str, Any]) -> BiomarkerDecisionContext:
        gen_at = self._parse_iso_datetime(d["generated_at"]) if d.get("generated_at") else None
        signals = tuple(
            BiomarkerDecisionSignal(
                canonical_code=sig["canonical_code"],
                interpretation=sig["interpretation"],
                confidence=sig["confidence"],
                summary=sig.get("summary"),
            )
            for sig in d.get("signals", [])
        )
        return BiomarkerDecisionContext(
            status=ContextDataStatus(d["status"]),
            attention_count=int(d["attention_count"]),
            critical_count=int(d["critical_count"]),
            signals=signals,
            generated_at=gen_at,
        )

    def _decode_performance(self, d: Dict[str, Any]) -> PerformanceDecisionContext:
        perf_at = self._parse_iso_datetime(d["performed_at"]) if d.get("performed_at") else None
        lt1 = self._decode_thresh(d.get("lt1"))
        lt2 = self._decode_thresh(d.get("lt2"))

        return PerformanceDecisionContext(
            status=ContextDataStatus(d["status"]),
            latest_test_id=d.get("latest_test_id"),
            latest_test_type=d.get("latest_test_type"),
            performed_at=perf_at,
            lt1=lt1,
            lt2=lt2,
        )

    def _decode_thresh(self, d: Dict[str, Any] | None) -> PerformanceThresholdSnapshot | None:
        if d is None:
            return None
        return PerformanceThresholdSnapshot(
            name=d["name"],
            status=d["status"],
            power_watts=float(d["power_watts"]) if d.get("power_watts") is not None else None,
            speed_kph=float(d["speed_kph"]) if d.get("speed_kph") is not None else None,
            heart_rate_bpm=int(d["heart_rate_bpm"]) if d.get("heart_rate_bpm") is not None else None,
            lactate_mmol_l=float(d["lactate_mmol_l"]) if d.get("lactate_mmol_l") is not None else None,
            confidence=float(d["confidence"]) if d.get("confidence") is not None else None,
            method=d.get("method"),
        )
