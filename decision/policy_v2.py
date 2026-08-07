from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from decision.context import AthleteDecisionContext, ContextDataStatus


class DecisionAction(str, Enum):
    PROCEED = "proceed"
    REDUCE = "reduce"
    REPLACE_WITH_RECOVERY = "replace_with_recovery"
    REST = "rest"
    REVIEW = "review"


class DecisionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DecisionPolicySignal:
    code: str
    source: str
    severity: DecisionSeverity
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be non-empty string")
        if not isinstance(self.severity, DecisionSeverity):
            raise TypeError("severity must be DecisionSeverity")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be non-empty string")


@dataclass(frozen=True)
class DecisionPolicyResult:
    generated_at: datetime
    action: DecisionAction
    severity: DecisionSeverity
    signals: tuple[DecisionPolicySignal, ...]
    confidence: float
    policy_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be datetime")
        if not isinstance(self.action, DecisionAction):
            raise TypeError("action must be DecisionAction")
        if not isinstance(self.severity, DecisionSeverity):
            raise TypeError("severity must be DecisionSeverity")
        if not isinstance(self.signals, tuple):
            raise TypeError("signals must be tuple")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty string")

        seen_codes: set[str] = set()
        for sig in self.signals:
            if not isinstance(sig, DecisionPolicySignal):
                raise TypeError("signals items must be DecisionPolicySignal")
            if sig.code in seen_codes:
                raise ValueError(f"Duplicate signal code: {sig.code}")
            seen_codes.add(sig.code)


class DecisionPolicyV2:
    """Stateless deterministic Decision Intelligence 2.0 Policy evaluator."""

    policy_version: str = "2.0"

    _ACTION_PRIORITY: dict[DecisionAction, int] = {
        DecisionAction.REST: 5,
        DecisionAction.REVIEW: 4,
        DecisionAction.REPLACE_WITH_RECOVERY: 3,
        DecisionAction.REDUCE: 2,
        DecisionAction.PROCEED: 1,
    }

    _SEVERITY_PRIORITY: dict[DecisionSeverity, int] = {
        DecisionSeverity.CRITICAL: 4,
        DecisionSeverity.HIGH: 3,
        DecisionSeverity.MEDIUM: 2,
        DecisionSeverity.LOW: 1,
    }

    _SEVERITY_CONFIDENCE: dict[DecisionSeverity, float] = {
        DecisionSeverity.CRITICAL: 0.95,
        DecisionSeverity.HIGH: 0.85,
        DecisionSeverity.MEDIUM: 0.70,
        DecisionSeverity.LOW: 0.60,
    }

    def evaluate(self, context: AthleteDecisionContext) -> DecisionPolicyResult:
        if not isinstance(context, AthleteDecisionContext):
            raise TypeError("context must be AthleteDecisionContext")

        signals: list[DecisionPolicySignal] = []

        # 1. Context rules
        if (
            context.recovery.status == ContextDataStatus.UNAVAILABLE
            and context.training.status == ContextDataStatus.UNAVAILABLE
            and context.biomarkers.status == ContextDataStatus.UNAVAILABLE
            and context.performance.status == ContextDataStatus.UNAVAILABLE
        ):
            signals.append(
                DecisionPolicySignal(
                    code="context_all_unavailable",
                    source="context",
                    severity=DecisionSeverity.HIGH,
                    summary="All decision context sources are unavailable.",
                )
            )

        if (
            context.recovery.status == ContextDataStatus.STALE
            or context.training.status == ContextDataStatus.STALE
            or context.biomarkers.status == ContextDataStatus.STALE
            or context.performance.status == ContextDataStatus.STALE
        ):
            signals.append(
                DecisionPolicySignal(
                    code="context_stale",
                    source="context",
                    severity=DecisionSeverity.MEDIUM,
                    summary="One or more decision context sources are stale.",
                )
            )

        # 2. Biomarkers rules
        if context.biomarkers.critical_count > 0:
            signals.append(
                DecisionPolicySignal(
                    code="biomarker_critical",
                    source="biomarkers",
                    severity=DecisionSeverity.CRITICAL,
                    summary="Critical laboratory signals require review.",
                )
            )
        elif context.biomarkers.attention_count > 0:
            signals.append(
                DecisionPolicySignal(
                    code="biomarker_attention",
                    source="biomarkers",
                    severity=DecisionSeverity.HIGH,
                    summary="Laboratory signals require attention.",
                )
            )

        # 3. Recovery rules
        rec_score = context.recovery.recovery_score
        if rec_score is not None:
            if rec_score < 40.0:
                signals.append(
                    DecisionPolicySignal(
                        code="recovery_very_low",
                        source="recovery",
                        severity=DecisionSeverity.CRITICAL,
                        summary="Recovery is too low for planned training.",
                    )
                )
            elif 40.0 <= rec_score < 60.0:
                signals.append(
                    DecisionPolicySignal(
                        code="recovery_low",
                        source="recovery",
                        severity=DecisionSeverity.HIGH,
                        summary="Recovery is below the preferred training range.",
                    )
                )
            elif 60.0 <= rec_score < 75.0:
                signals.append(
                    DecisionPolicySignal(
                        code="recovery_moderate",
                        source="recovery",
                        severity=DecisionSeverity.MEDIUM,
                        summary="Training should be performed conservatively.",
                    )
                )
            elif rec_score >= 75.0:
                signals.append(
                    DecisionPolicySignal(
                        code="recovery_ready",
                        source="recovery",
                        severity=DecisionSeverity.LOW,
                        summary="Recovery supports the planned session.",
                    )
                )

        # 4. Training rules
        if context.training.fatigue_status == "high":
            signals.append(
                DecisionPolicySignal(
                    code="training_fatigue_high",
                    source="training",
                    severity=DecisionSeverity.HIGH,
                    summary="Recent fatigue requires a lower training load.",
                )
            )

        if context.training.planned_session_type is None and context.training.status != ContextDataStatus.UNAVAILABLE:
            signals.append(
                DecisionPolicySignal(
                    code="training_plan_missing",
                    source="training",
                    severity=DecisionSeverity.MEDIUM,
                    summary="No planned training session is available.",
                )
            )

        # 5. Performance rules
        if context.performance.status == ContextDataStatus.AVAILABLE:
            lt1_invalid = context.performance.lt1 is not None and context.performance.lt1.status == "invalid_curve"
            lt2_invalid = context.performance.lt2 is not None and context.performance.lt2.status == "invalid_curve"
            if lt1_invalid or lt2_invalid:
                signals.append(
                    DecisionPolicySignal(
                        code="performance_threshold_invalid",
                        source="performance",
                        severity=DecisionSeverity.MEDIUM,
                        summary="Performance threshold analysis requires review.",
                    )
                )

        # Fallback if no rule triggered
        if not signals:
            signals.append(
                DecisionPolicySignal(
                    code="context_no_actionable_signal",
                    source="context",
                    severity=DecisionSeverity.LOW,
                    summary="No actionable decision signals were detected.",
                )
            )

        # Resolve winning action & winning severity
        winning_action = self._determine_winning_action(signals)
        max_severity = max(signals, key=lambda s: self._SEVERITY_PRIORITY[s.severity]).severity
        confidence = self._SEVERITY_CONFIDENCE[max_severity]

        return DecisionPolicyResult(
            generated_at=context.generated_at,
            action=winning_action,
            severity=max_severity,
            signals=tuple(signals),
            confidence=confidence,
            policy_version=self.policy_version,
        )

    def _determine_winning_action(self, signals: list[DecisionPolicySignal]) -> DecisionAction:
        highest_prio = 0
        winning_action = DecisionAction.PROCEED

        for sig in signals:
            act = self._map_signal_to_action(sig)
            prio = self._ACTION_PRIORITY[act]
            if prio > highest_prio:
                highest_prio = prio
                winning_action = act

        return winning_action

    @staticmethod
    def _map_signal_to_action(sig: DecisionPolicySignal) -> DecisionAction:
        if sig.code in ("biomarker_critical", "recovery_very_low"):
            return DecisionAction.REST
        if sig.code in (
            "context_all_unavailable",
            "context_stale",
            "biomarker_attention",
            "training_plan_missing",
            "performance_threshold_invalid",
        ):
            return DecisionAction.REVIEW
        if sig.code == "recovery_low":
            return DecisionAction.REPLACE_WITH_RECOVERY
        if sig.code in ("recovery_moderate", "training_fatigue_high"):
            return DecisionAction.REDUCE
        return DecisionAction.PROCEED
