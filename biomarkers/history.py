"""
Biomarker History Read Model and Time Series Builder for Biomarkers Domain (Sprint 7D.1).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from biomarkers.models import LaboratoryObservation, VerificationStatus
from biomarkers.registry import BiomarkerRegistry
from biomarkers.repository import LaboratoryRepository


@dataclass(frozen=True)
class BiomarkerMeasurement:
    """Immutable single historical measurement for a canonical biomarker."""

    collected_at: datetime
    numeric_value: Optional[float]
    qualitative_value: Optional[str]
    laboratory_flag: Optional[str]
    verification_status: VerificationStatus

    def __post_init__(self) -> None:
        if self.collected_at is None:
            raise ValueError("collected_at is required.")
        if self.collected_at.tzinfo is None:
            object.__setattr__(self, "collected_at", self.collected_at.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class BiomarkerHistory:
    """Immutable historical time series read model for a canonical biomarker."""

    canonical_code: str
    display_name: str
    preferred_unit: str
    measurements: Tuple[BiomarkerMeasurement, ...]

    def __post_init__(self) -> None:
        if not self.canonical_code or not self.canonical_code.strip():
            raise ValueError("canonical_code cannot be empty.")
        if not self.display_name or not self.display_name.strip():
            raise ValueError("display_name cannot be empty.")


class BiomarkerHistoryBuilder:
    """
    Builder engine constructing BiomarkerHistory read models from repository observations.
    Preserves strict chronological ordering (oldest -> newest), timezone safety, and deterministic deduplication.
    """

    def __init__(
        self,
        repository: LaboratoryRepository,
        biomarker_registry: Optional[BiomarkerRegistry] = None,
    ) -> None:
        self.repository = repository
        self.biomarker_registry = biomarker_registry

    def build_for_code(self, canonical_code: str) -> BiomarkerHistory:
        """Builds BiomarkerHistory for a specific canonical_code."""
        if not canonical_code or not canonical_code.strip():
            raise ValueError("canonical_code cannot be empty.")

        code = canonical_code.strip().lower()
        grouped_obs = self.repository.get_active_observations_grouped_by_canonical_code()
        obs_tuple = grouped_obs.get(code, ())

        display_name = code
        preferred_unit = ""

        if self.biomarker_registry:
            definition = self.biomarker_registry.get(code)
            if definition:
                display_name = definition.canonical_name
                preferred_unit = definition.default_unit

        measurements, fallback_unit = self._build_measurements(obs_tuple)

        if not preferred_unit and fallback_unit:
            preferred_unit = fallback_unit

        return BiomarkerHistory(
            canonical_code=code,
            display_name=display_name,
            preferred_unit=preferred_unit,
            measurements=measurements,
        )

    def build_all(self) -> Dict[str, BiomarkerHistory]:
        """Builds BiomarkerHistory for all canonical codes present in active repository observations or registry."""
        grouped_obs = self.repository.get_active_observations_grouped_by_canonical_code()
        histories: Dict[str, BiomarkerHistory] = {}

        codes = set(grouped_obs.keys())
        if self.biomarker_registry:
            codes.update(d.canonical_code for d in self.biomarker_registry.list_definitions())

        for code in sorted(codes):
            histories[code] = self.build_for_code(code)

        return histories

    def _build_measurements(
        self, observations: Tuple[LaboratoryObservation, ...]
    ) -> Tuple[Tuple[BiomarkerMeasurement, ...], str]:
        """
        Sorts observations chronologically (oldest -> newest) and deduplicates identical readings.
        """
        if not observations:
            return (), ""

        prepared: List[Tuple[datetime, int, str, LaboratoryObservation]] = []
        for obs in observations:
            dt = obs.collected_at
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            row_idx = getattr(obs, "report_row_index", 0)
            obs_id = obs.observation_id
            prepared.append((dt, row_idx, obs_id, obs))

        # Sort chronologically: oldest -> newest, then by report_row_index and observation_id for deterministic order
        prepared.sort(key=lambda item: (item[0], item[1], item[2]))

        measurements: List[BiomarkerMeasurement] = []
        seen_keys = set()
        fallback_unit = ""

        for dt, _, _, obs in prepared:
            num_val = obs.normalized_value if obs.normalized_value is not None else obs.numeric_value
            qual_val = obs.text_value or obs.qualitative_value or (obs.raw_value if num_val is None else None)
            flag = obs.laboratory_flag

            unit_candidate = obs.normalized_unit or obs.raw_unit
            if unit_candidate and not fallback_unit:
                fallback_unit = unit_candidate

            dedup_key = (dt.isoformat(), num_val, qual_val, flag, obs.verification_status.value)
            if dedup_key in seen_keys:
                continue

            seen_keys.add(dedup_key)
            measurements.append(
                BiomarkerMeasurement(
                    collected_at=dt,
                    numeric_value=num_val,
                    qualitative_value=qual_val,
                    laboratory_flag=flag,
                    verification_status=obs.verification_status,
                )
            )

        return tuple(measurements), fallback_unit
