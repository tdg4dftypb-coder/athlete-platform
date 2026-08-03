from adaptive import BodyMassTrendQualityInput
from body_composition import BodyCompositionAssessment, BodyCompositionInput


class BodyMassTrendQualityInputBuilder:
    """Prepare explicit trend-quality facts from already-normalized data."""

    def build(
        self,
        assessment: BodyCompositionAssessment,
        body_composition_input: BodyCompositionInput,
    ) -> BodyMassTrendQualityInput:
        if assessment.valid_for_date != body_composition_input.valid_for_date:
            raise ValueError("valid_for_date must match assessment")
        if assessment.as_of != body_composition_input.as_of:
            raise ValueError("as_of must match assessment")

        measurement_dates = {
            observation.observed_for_date
            for observation in body_composition_input.observations
            if observation.body_mass_kg is not None
        }
        evidence = tuple(
            sorted(
                set(assessment.evidence).union(body_composition_input.evidence)
            )
        )

        return BodyMassTrendQualityInput(
            assessment=assessment,
            measurement_count=len(measurement_dates),
            source_consistency_known=False,
            valid_for_date=assessment.valid_for_date,
            as_of=assessment.as_of,
            evidence=evidence,
        )
