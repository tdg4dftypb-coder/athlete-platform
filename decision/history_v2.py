from dataclasses import dataclass
from datetime import datetime

from decision.context import AthleteDecisionContext
from decision.policy_v2 import DecisionPolicyResult
from decision.recommendation_plan import RecommendationPlan


@dataclass(frozen=True)
class DecisionAuditRecord:
    decision_id: str
    recorded_at: datetime
    context: AthleteDecisionContext
    policy_result: DecisionPolicyResult
    recommendation_plan: RecommendationPlan

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise ValueError("decision_id must be non-empty string")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be datetime")
        if not isinstance(self.context, AthleteDecisionContext):
            raise TypeError("context must be AthleteDecisionContext")
        if not isinstance(self.policy_result, DecisionPolicyResult):
            raise TypeError("policy_result must be DecisionPolicyResult")
        if not isinstance(self.recommendation_plan, RecommendationPlan):
            raise TypeError("recommendation_plan must be RecommendationPlan")

        # Temporal consistency
        if self.policy_result.generated_at != self.context.generated_at:
            raise ValueError("policy_result.generated_at must match context.generated_at")
        if self.recommendation_plan.generated_at != self.policy_result.generated_at:
            raise ValueError("recommendation_plan.generated_at must match policy_result.generated_at")

        # Result & Plan consistency
        if self.recommendation_plan.action != self.policy_result.action:
            raise ValueError("recommendation_plan.action must match policy_result.action")
        if self.recommendation_plan.severity != self.policy_result.severity:
            raise ValueError("recommendation_plan.severity must match policy_result.severity")
        if self.recommendation_plan.confidence != self.policy_result.confidence:
            raise ValueError("recommendation_plan.confidence must match policy_result.confidence")
        if self.recommendation_plan.policy_version != self.policy_result.policy_version:
            raise ValueError("recommendation_plan.policy_version must match policy_result.policy_version")

        # Explanation items consistency with signals
        items = self.recommendation_plan.explanation.items
        signals = self.policy_result.signals
        if len(items) != len(signals):
            raise ValueError("explanation.items count must match policy_result.signals count")

        for idx, (item, sig) in enumerate(zip(items, signals)):
            if item.signal_code != sig.code:
                raise ValueError(f"Explanation item {idx} signal_code '{item.signal_code}' does not match signal code '{sig.code}'")
            if item.source != sig.source:
                raise ValueError(f"Explanation item {idx} source '{item.source}' does not match signal source '{sig.source}'")
            if item.severity != sig.severity:
                raise ValueError(f"Explanation item {idx} severity '{item.severity}' does not match signal severity '{sig.severity}'")
            if item.summary != sig.summary:
                raise ValueError(f"Explanation item {idx} summary '{item.summary}' does not match signal summary '{sig.summary}'")


@dataclass(frozen=True)
class DecisionHistory:
    records: tuple[DecisionAuditRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise TypeError("records must be tuple")

        seen_ids: set[str] = set()
        prev_generated_at: datetime | None = None
        prev_id: str | None = None

        for rec in self.records:
            if not isinstance(rec, DecisionAuditRecord):
                raise TypeError("records items must be DecisionAuditRecord")
            if rec.decision_id in seen_ids:
                raise ValueError(f"Duplicate decision_id in history: {rec.decision_id}")
            seen_ids.add(rec.decision_id)

            curr_gen = rec.context.generated_at
            if prev_generated_at is not None:
                if curr_gen < prev_generated_at:
                    raise ValueError("records must be sorted chronologically by context.generated_at ascending")
                if curr_gen == prev_generated_at:
                    if prev_id is not None and rec.decision_id <= prev_id:
                        raise ValueError("records with identical timestamp must be sorted by decision_id ascending")

            prev_generated_at = curr_gen
            prev_id = rec.decision_id


class DecisionAuditRecordBuilder:
    """Stateless builder creating DecisionAuditRecord with validation."""

    def build(
        self,
        decision_id: str,
        recorded_at: datetime,
        context: AthleteDecisionContext,
        policy_result: DecisionPolicyResult,
        recommendation_plan: RecommendationPlan,
    ) -> DecisionAuditRecord:
        return DecisionAuditRecord(
            decision_id=decision_id,
            recorded_at=recorded_at,
            context=context,
            policy_result=policy_result,
            recommendation_plan=recommendation_plan,
        )


class DecisionHistoryBuilder:
    """Stateless builder aggregating, deduplicating, and sorting DecisionAuditRecords into DecisionHistory."""

    def build(self, records: tuple[DecisionAuditRecord, ...]) -> DecisionHistory:
        if not isinstance(records, tuple):
            raise TypeError("records must be tuple")

        # Deduplication: keep record with latest recorded_at for duplicate decision_id.
        # Tie-breaker for identical recorded_at: keep last occurrence in input tuple.
        by_id: dict[str, tuple[int, DecisionAuditRecord]] = {}
        for idx, rec in enumerate(records):
            if not isinstance(rec, DecisionAuditRecord):
                raise TypeError("records items must be DecisionAuditRecord")

            d_id = rec.decision_id
            if d_id not in by_id:
                by_id[d_id] = (idx, rec)
            else:
                prev_idx, prev_rec = by_id[d_id]
                if rec.recorded_at > prev_rec.recorded_at:
                    by_id[d_id] = (idx, rec)
                elif rec.recorded_at == prev_rec.recorded_at:
                    by_id[d_id] = (idx, rec)  # Last occurrence in input

        unique_records = [item[1] for item in by_id.values()]

        # Sort: 1. context.generated_at ascending, 2. decision_id ascending
        sorted_records = sorted(
            unique_records,
            key=lambda r: (r.context.generated_at, r.decision_id),
        )

        return DecisionHistory(records=tuple(sorted_records))
