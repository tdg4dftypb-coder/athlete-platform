"""Performance Lab — test session builder.

Stateless builder that maps PerformanceTestSessionInput to a domain
PerformanceTestSession. No sorting, no coercion, no state.
"""
from __future__ import annotations

from performance_lab.domain import PerformanceStage, PerformanceTestSession
from performance_lab.input_models import (
    PerformanceStageInput,
    PerformanceTestSessionInput,
)


class PerformanceTestSessionBuilder:
    """Maps raw input to a validated domain PerformanceTestSession.

    - Stateless: no instance state is mutated or cached between builds.
    - Transparent: unsorted or invalid input surfaces as domain ValueError/TypeError.
    - No coercion: strings are not converted to numbers; values are passed as-is.
    """

    def build(self, input_data: PerformanceTestSessionInput) -> PerformanceTestSession:
        """Build a PerformanceTestSession from the given input.

        Raises:
            ValueError: when domain invariants are violated (e.g. unsorted
                stages, duplicate stage_number, negative values).
            TypeError: when stages are not a tuple.
        """
        stages = tuple(
            self._build_stage(stage_input)
            for stage_input in input_data.stages
        )
        return PerformanceTestSession(
            test_id=input_data.test_id,
            performed_at=input_data.performed_at,
            test_type=input_data.test_type,
            status=input_data.status,
            modality=input_data.modality,
            stages=stages,
            protocol_name=input_data.protocol_name,
            body_mass_kg=input_data.body_mass_kg,
            ambient_temperature_c=input_data.ambient_temperature_c,
            notes=input_data.notes,
        )

    @staticmethod
    def _build_stage(stage_input: PerformanceStageInput) -> PerformanceStage:
        return PerformanceStage(
            stage_number=stage_input.stage_number,
            completion_status=stage_input.completion_status,
            duration_seconds=stage_input.duration_seconds,
            power_watts=stage_input.power_watts,
            speed_kph=stage_input.speed_kph,
            heart_rate_bpm=stage_input.heart_rate_bpm,
            lactate_mmol_l=stage_input.lactate_mmol_l,
            cadence_rpm=stage_input.cadence_rpm,
            perceived_exertion=stage_input.perceived_exertion,
            notes=stage_input.notes,
        )
