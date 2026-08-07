from datetime import datetime

from decision.context import (
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
)
from morning_briefing.input_models import BiomarkerBriefingInput, MorningBriefingInput
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


class DefaultBiomarkerDecisionContextAdapter:
    """Adapter converting Biomarker input from MorningBriefingInputProvider or MorningBriefingInput to BiomarkerDecisionContext."""

    def __init__(self, provider: MorningBriefingInputProvider) -> None:
        if provider is None:
            raise TypeError("provider must not be None")
        self._provider = provider

    def get_context(
        self,
        generated_at: datetime,
        briefing_input: MorningBriefingInput | None = None,
    ) -> BiomarkerDecisionContext:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")

        if briefing_input is None:
            try:
                briefing_input = self._provider.get_input()
            except MorningBriefingInputError:
                return BiomarkerDecisionContext(
                    status=ContextDataStatus.UNAVAILABLE,
                    attention_count=0,
                    critical_count=0,
                    signals=(),
                )

        if briefing_input is None or briefing_input.biomarkers is None:
            return BiomarkerDecisionContext(
                status=ContextDataStatus.UNAVAILABLE,
                attention_count=0,
                critical_count=0,
                signals=(),
            )

        bio: BiomarkerBriefingInput = briefing_input.biomarkers

        # Map data_status to ContextDataStatus
        if bio.data_status == "unavailable":
            status = ContextDataStatus.UNAVAILABLE
        elif bio.is_stale:
            status = ContextDataStatus.STALE
        elif bio.data_status == "partial":
            status = ContextDataStatus.PARTIAL
        else:
            status = ContextDataStatus.AVAILABLE

        # Map BiomarkerBriefingSignalInput instances to BiomarkerDecisionSignal
        mapped_signals: list[BiomarkerDecisionSignal] = []
        for sig in getattr(bio, "signals", ()) or ():
            mapped_signals.append(
                BiomarkerDecisionSignal(
                    canonical_code=sig.canonical_code,
                    interpretation=sig.interpretation,
                    confidence=sig.data_quality,
                    summary=sig.summary,
                )
            )

        # Sort mapped signals deterministically strictly by canonical_code
        signals_sorted = tuple(sorted(mapped_signals, key=lambda s: s.canonical_code))

        return BiomarkerDecisionContext(
            status=status,
            attention_count=bio.attention_count,
            critical_count=bio.critical_count,
            signals=signals_sorted,
            generated_at=briefing_input.generated_at,
        )
