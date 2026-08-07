from dataclasses import dataclass
from datetime import datetime

from decision.context_provider import AthleteDecisionContextProvider
from decision.history_v2 import DecisionAuditRecord, DecisionAuditRecordBuilder
from decision.policy_v2 import DecisionPolicyV2
from decision.recommendation_plan import RecommendationPlanBuilder


@dataclass(frozen=True)
class DecisionExecutionRequest:
    decision_id: str
    generated_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise ValueError("decision_id must be non-empty string")
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be datetime")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be datetime")


@dataclass(frozen=True)
class DecisionExecutionResult:
    request: DecisionExecutionRequest
    record: DecisionAuditRecord

    def __post_init__(self) -> None:
        if not isinstance(self.request, DecisionExecutionRequest):
            raise TypeError("request must be DecisionExecutionRequest")
        if not isinstance(self.record, DecisionAuditRecord):
            raise TypeError("record must be DecisionAuditRecord")

        if self.record.decision_id != self.request.decision_id:
            raise ValueError("record.decision_id must match request.decision_id")
        if self.record.context.generated_at != self.request.generated_at:
            raise ValueError("record.context.generated_at must match request.generated_at")
        if self.record.policy_result.generated_at != self.request.generated_at:
            raise ValueError("record.policy_result.generated_at must match request.generated_at")
        if self.record.recommendation_plan.generated_at != self.request.generated_at:
            raise ValueError("record.recommendation_plan.generated_at must match request.generated_at")
        if self.record.recorded_at != self.request.recorded_at:
            raise ValueError("record.recorded_at must match request.recorded_at")


class DecisionExecutionService:
    """Application orchestrator running the complete Decision Intelligence 2.0 pipeline."""

    def __init__(
        self,
        context_provider: AthleteDecisionContextProvider,
        policy: DecisionPolicyV2 | None = None,
        recommendation_builder: RecommendationPlanBuilder | None = None,
        audit_record_builder: DecisionAuditRecordBuilder | None = None,
    ) -> None:
        if context_provider is None:
            raise TypeError("context_provider must not be None")
        self._context_provider = context_provider
        self._policy = policy or DecisionPolicyV2()
        self._recommendation_builder = recommendation_builder or RecommendationPlanBuilder()
        self._audit_record_builder = audit_record_builder or DecisionAuditRecordBuilder()

    def execute(self, request: DecisionExecutionRequest) -> DecisionExecutionResult:
        if not isinstance(request, DecisionExecutionRequest):
            raise TypeError("request must be DecisionExecutionRequest")

        # 1. Build decision context
        context = self._context_provider.build_context(generated_at=request.generated_at)

        # 2. Evaluate policy
        policy_result = self._policy.evaluate(context)

        # 3. Build recommendation plan & explanation
        recommendation_plan = self._recommendation_builder.build(policy_result)

        # 4. Build audit record
        record = self._audit_record_builder.build(
            decision_id=request.decision_id,
            recorded_at=request.recorded_at,
            context=context,
            policy_result=policy_result,
            recommendation_plan=recommendation_plan,
        )

        # 5. Return execution result
        return DecisionExecutionResult(
            request=request,
            record=record,
        )
