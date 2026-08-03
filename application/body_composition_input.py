from __future__ import annotations

from datetime import datetime

from body_composition import BodyCompositionInput, BodyCompositionObservation
from core.models import HealthDaily


class BodyCompositionInputBuilder:
    """Adapt in-memory health facts to a normalized BodyCompositionInput."""

    def build(
        self,
        *,
        health_history: tuple[HealthDaily, ...],
        as_of: datetime,
    ) -> BodyCompositionInput:
        valid_for_date = as_of.date()
        normalized_records = {
            (item.date, item.weight)
            for item in health_history
            if item.date <= valid_for_date and item.weight is not None
        }
        observations = tuple(
            BodyCompositionObservation(
                observed_for_date=observed_for_date,
                body_mass_kg=body_mass_kg,
                evidence=(f"body_mass:{observed_for_date.isoformat()}",),
            )
            for observed_for_date, body_mass_kg in sorted(normalized_records)
        )
        evidence = tuple(
            sorted(
                {
                    evidence_item
                    for observation in observations
                    for evidence_item in observation.evidence
                }
            )
        )

        return BodyCompositionInput(
            observations=observations,
            valid_for_date=valid_for_date,
            as_of=as_of,
            evidence=evidence,
        )
