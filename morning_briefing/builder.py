from morning_briefing.domain import (
    MorningBriefing,
    MorningSection,
    MorningMetric,
    MorningStatus,
)
from morning_briefing.input_models import MorningBriefingInput


class MorningBriefingBuilder:
    def build(self, input_data: MorningBriefingInput) -> MorningBriefing:
        sections = []

        # 1. Recovery Section
        if input_data.recovery is not None:
            rec = input_data.recovery
            metrics = (
                MorningMetric(
                    title="Recovery score",
                    value=rec.score if rec.score is not None else None,
                    unit="%",
                    status="info",
                ),
                MorningMetric(
                    title="Recovery status",
                    value=rec.status if rec.status is not None else None,
                    unit=None,
                    status="info",
                ),
            )
            sections.append(
                MorningSection(
                    title="Recovery",
                    summary=rec.summary if rec.summary is not None else "",
                    metrics=metrics,
                    recommendations=(),
                )
            )

        # 2. Training Section
        if input_data.training is not None and input_data.training.is_available:
            trn = input_data.training
            metrics = (
                MorningMetric(
                    title="Session",
                    value=trn.title if trn.title is not None else None,
                    unit=None,
                    status="info",
                ),
                MorningMetric(
                    title="Duration",
                    value=trn.duration_minutes if trn.duration_minutes is not None else None,
                    unit="min",
                    status="info",
                ),
                MorningMetric(
                    title="Intensity",
                    value=trn.intensity if trn.intensity is not None else None,
                    unit=None,
                    status="info",
                ),
            )
            sections.append(
                MorningSection(
                    title="Training",
                    summary=trn.description if trn.description is not None else "",
                    metrics=metrics,
                    recommendations=(),
                )
            )

        # 3. Biomarkers Section
        if input_data.biomarkers is not None:
            bio = input_data.biomarkers
            metrics = (
                MorningMetric(
                    title="Available results",
                    value=bio.available_count,
                    unit=None,
                    status="info",
                ),
                MorningMetric(
                    title="Results requiring attention",
                    value=bio.attention_count,
                    unit=None,
                    status="warning" if bio.attention_count > 0 else "info",
                ),
            )
            sections.append(
                MorningSection(
                    title="Biomarkers",
                    summary=bio.summary if bio.summary is not None else "",
                    metrics=metrics,
                    recommendations=(),
                )
            )

        # Determine status
        status = MorningStatus.UNAVAILABLE
        if len(sections) > 0:
            is_stale_recovery = input_data.recovery.is_stale if input_data.recovery is not None else False
            is_stale_biomarkers = input_data.biomarkers.is_stale if input_data.biomarkers is not None else False

            if is_stale_recovery or is_stale_biomarkers:
                status = MorningStatus.STALE
            else:
                # Expecting 3 sections for READY
                # But Training section is only expected if it is present in input
                has_recovery = input_data.recovery is not None
                has_biomarkers = input_data.biomarkers is not None
                # If training is present but is_available=False, we won't build Training Section, meaning partial briefing.
                # If training is absent in input completely, we can consider that section as absent.
                # So we are READY when we have Recovery, Training (is_available=True), and Biomarkers sections built.
                has_training_section = input_data.training is not None and input_data.training.is_available
                
                # If input has all three inputs provided, and all three sections are built, then READY.
                if has_recovery and has_biomarkers and (input_data.training is not None and has_training_section):
                    status = MorningStatus.READY
                else:
                    status = MorningStatus.PARTIAL

        return MorningBriefing(
            generated_at=input_data.generated_at,
            status=status,
            sections=tuple(sections),
        )
