from __future__ import annotations

import dataclasses
from typing import Optional, Union
from morning_briefing.domain import (
    MorningBriefing,
    MorningSection,
    MorningMetric,
    MorningRecommendation,
    MorningPriority,
    MorningStatus,
)


def _as_numeric(value: Union[int, float, str, None]) -> Optional[float]:
    """Safely coerce a metric value to float. Returns None for non-numeric values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def _section_by_title(sections: tuple[MorningSection, ...], title: str) -> Optional[MorningSection]:
    for section in sections:
        if section.title == title:
            return section
    return None


def _metric_by_title(section: MorningSection, title: str) -> Optional[MorningMetric]:
    for metric in section.metrics:
        if metric.title == title:
            return metric
    return None


def _is_duplicate(
    existing: tuple[MorningRecommendation, ...],
    rec: MorningRecommendation,
) -> bool:
    return any(
        r.title == rec.title and r.description == rec.description and r.priority == rec.priority
        for r in existing
    )


def _add_recommendation_to_section(
    section: MorningSection,
    rec: MorningRecommendation,
) -> MorningSection:
    if _is_duplicate(section.recommendations, rec):
        return section
    return dataclasses.replace(
        section,
        recommendations=section.recommendations + (rec,),
    )


def _replace_section(
    sections: tuple[MorningSection, ...],
    updated: MorningSection,
) -> tuple[MorningSection, ...]:
    return tuple(updated if s.title == updated.title else s for s in sections)


class MorningRecommendationEngine:
    """Deterministic recommendation engine for Morning Briefing.

    Analyses sections and metrics of an existing MorningBriefing and
    returns a new immutable instance enriched with recommendations.
    Does not modify the input object.
    """

    def apply(self, briefing: MorningBriefing) -> MorningBriefing:
        sections = briefing.sections

        # --- Rule 7 — STALE briefing ---
        # Applied first so it lands in the first available section
        if briefing.status == MorningStatus.STALE and len(sections) > 0:
            stale_rec = MorningRecommendation(
                title="Refresh source data",
                description="Some briefing information may be outdated.",
                priority=MorningPriority.MEDIUM,
            )
            first_section = _add_recommendation_to_section(sections[0], stale_rec)
            sections = _replace_section(sections, first_section)

        # --- Rule 2 / 3 / 4 — Recovery score ---
        recovery_section = _section_by_title(sections, "Recovery")
        if recovery_section is not None:
            score_metric = _metric_by_title(recovery_section, "Recovery score")
            if score_metric is not None:
                score = _as_numeric(score_metric.value)
                if score is not None:
                    if score < 50:
                        rec = MorningRecommendation(
                            title="Prioritize recovery",
                            description="Reduce training intensity and prioritize sleep, hydration, and recovery.",
                            priority=MorningPriority.HIGH,
                        )
                    elif score < 70:
                        rec = MorningRecommendation(
                            title="Train conservatively",
                            description="Keep today's training controlled and monitor how you feel.",
                            priority=MorningPriority.MEDIUM,
                        )
                    else:
                        rec = MorningRecommendation(
                            title="Proceed as planned",
                            description="Recovery indicators support the planned training session.",
                            priority=MorningPriority.LOW,
                        )
                    updated_recovery = _add_recommendation_to_section(recovery_section, rec)
                    sections = _replace_section(sections, updated_recovery)

        # --- Rule 6 — Biomarkers requiring attention ---
        bio_section = _section_by_title(sections, "Biomarkers")
        if bio_section is not None:
            attention_metric = _metric_by_title(bio_section, "Results requiring attention")
            if attention_metric is not None:
                attention = _as_numeric(attention_metric.value)
                if attention is not None and attention > 0:
                    bio_rec = MorningRecommendation(
                        title="Review laboratory results",
                        description="One or more laboratory results require attention.",
                        priority=MorningPriority.HIGH,
                    )
                    updated_bio = _add_recommendation_to_section(bio_section, bio_rec)
                    sections = _replace_section(sections, updated_bio)

        return dataclasses.replace(briefing, sections=sections)
