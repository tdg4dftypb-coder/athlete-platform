"""
Biomarkers Read Model, Summaries, Data Quality, and Dashboard Builder.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from biomarkers.models import (
    BiomarkerCategory,
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReport,
    NormalizationStatus,
    PlatformMessageLevel,
    VerificationStatus,
)
from biomarkers.registry import BiomarkerRegistry


class BiomarkersDashboardStatus(Enum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


# Friendly PL category names for presentation mapping
CATEGORY_DISPLAY_NAMES: Dict[BiomarkerCategory, str] = {
    BiomarkerCategory.MORPHOLOGY: "Morfologia",
    BiomarkerCategory.IRON_PANEL: "Gospodarka żelazowa",
    BiomarkerCategory.HORMONES: "Hormony",
    BiomarkerCategory.LIPIDS: "Lipidy",
    BiomarkerCategory.VITAMINS: "Witaminy",
    BiomarkerCategory.ELECTROLYTES: "Elektrolity",
    BiomarkerCategory.INFLAMMATORY_MARKERS: "Markery zapalne",
    BiomarkerCategory.URINALYSIS: "Badania moczu",
    BiomarkerCategory.OTHER: "Inne biomarkery",
}


@dataclass(frozen=True)
class BiomarkersDashboardMetadata:
    """Immutable read-side metadata header for BiomarkersDashboard."""

    status: BiomarkersDashboardStatus
    completeness_score: float
    limitations: Tuple[str, ...] = ()
    evidence: Tuple[str, ...] = ()
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_as_of: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.completeness_score <= 1.0):
            raise ValueError("completeness_score must be between 0.0 and 1.0.")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at datetime must be timezone-aware.")
        if self.data_as_of is not None and self.data_as_of.tzinfo is None:
            raise ValueError("data_as_of datetime must be timezone-aware.")


@dataclass(frozen=True)
class BiomarkerSummary:
    """Immutable summary representation of a single biomarker in the Read Model."""

    canonical_code: str
    canonical_name: str
    category: BiomarkerCategory
    latest_observation_id: str
    latest_value: Optional[float]
    latest_text_value: Optional[str]
    inequality_operator: Optional[str]
    normalized_unit: Optional[str]
    raw_unit: str
    laboratory_reference_text: Optional[str]
    laboratory_flag: Optional[str]
    laboratory_provided_critical_flag: Optional[str]
    collected_at: datetime
    trend_direction: str  # "increasing", "decreasing", "stable", "unavailable"
    trend_available: bool
    observation_count: int
    verification_status: VerificationStatus
    data_quality: str  # "high", "medium", "low"
    limitations: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.canonical_code:
            raise ValueError("canonical_code cannot be empty.")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at datetime must be timezone-aware.")


@dataclass(frozen=True)
class BiomarkerCategorySummary:
    """Immutable category grouping of biomarker summaries."""

    category: BiomarkerCategory
    display_name: str
    biomarkers: Tuple[BiomarkerSummary, ...]
    attention_count: int
    unresolved_count: int
    limitations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class UnresolvedBiomarkerItem:
    """Immutable public summary item for an unresolved observation requiring review."""

    observation_id: str
    raw_name: str
    raw_unit: str
    collected_at: datetime
    requires_review: bool
    normalization_status: NormalizationStatus
    safe_reason: str

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("observation_id cannot be empty.")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at datetime must be timezone-aware.")


@dataclass(frozen=True)
class BiomarkersDashboard:
    """Immutable root Read Model for Biomarkers & Laboratory Intelligence (v1.0)."""

    contract_version: str
    metadata: BiomarkersDashboardMetadata
    total_reports: int
    active_reports: int
    total_observations: int
    verified_observations: int
    unresolved_observations: int
    possible_duplicates: int
    latest_collection_date: Optional[str]
    categories: Tuple[BiomarkerCategorySummary, ...]
    unresolved_items: Tuple[UnresolvedBiomarkerItem, ...]
    data_quality_summary: Dict[str, Any]


class BiomarkersDashboardBuilder:
    """
    Builder engine for constructing BiomarkersDashboard Read Model instances from repository state.
    Uses ONLY active ImportRun observations. Evaluates deterministic trend direction and completeness.
    """

    def __init__(
        self,
        repository: Any,
        biomarker_registry: BiomarkerRegistry,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.repository = repository
        self.biomarker_registry = biomarker_registry
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def build(self) -> BiomarkersDashboard:
        """Builds the BiomarkersDashboard Read Model."""
        now = self.clock()

        # Collect active runs and active observations across all reports in repository
        active_observations: List[LaboratoryObservation] = []
        reports_count = 0
        active_reports_count = 0
        latest_coll_dt: Optional[datetime] = None

        # Fetch reports list if repository supports get_all_reports or fallback to _reports
        if hasattr(self.repository, "get_all_reports"):
            reports = self.repository.get_all_reports()
        else:
            reports = tuple(getattr(self.repository, "_reports", {}).values())
        reports_count = len(reports)

        for report in reports:
            active_run = self.repository.get_active_import_run(report.report_id)
            if active_run and active_run.active:
                active_reports_count += 1
                for obs in active_run.observations:
                    active_observations.append(obs)
                    if latest_coll_dt is None or obs.collected_at > latest_coll_dt:
                        latest_coll_dt = obs.collected_at

        total_obs_cnt = len(active_observations)
        verified_cnt = sum(1 for o in active_observations if o.verification_status == VerificationStatus.VERIFIED)
        unresolved_cnt = sum(1 for o in active_observations if o.normalization_status == NormalizationStatus.UNRESOLVED)
        possible_dup_cnt = sum(1 for o in active_observations if o.is_possible_duplicate)

        unresolved_items: List[UnresolvedBiomarkerItem] = []
        resolved_by_code: Dict[str, List[LaboratoryObservation]] = {}

        for obs in active_observations:
            # REJECTED observations can NEVER be used for main presentation
            if obs.verification_status == VerificationStatus.REJECTED:
                continue

            if obs.normalization_status == NormalizationStatus.UNRESOLVED or not obs.canonical_code:
                unresolved_items.append(
                    UnresolvedBiomarkerItem(
                        observation_id=obs.observation_id,
                        raw_name=obs.raw_name,
                        raw_unit=obs.raw_unit or "",
                        collected_at=obs.collected_at,
                        requires_review=obs.requires_review,
                        normalization_status=obs.normalization_status,
                        safe_reason="Unresolved biomarker alias requires review.",
                    )
                )
            else:
                code = obs.canonical_code.lower()
                resolved_by_code.setdefault(code, []).append(obs)

        # Build BiomarkerSummary for each canonical_code group
        biomarker_summaries: List[BiomarkerSummary] = []

        for code, obs_list in resolved_by_code.items():
            definition = self.biomarker_registry.get(code, include_inactive=True)
            if not definition:
                continue

            # Sort observations chronologically by collected_at, tie-breaker observation_id
            sorted_obs = sorted(obs_list, key=lambda o: (o.collected_at, o.observation_id))
            latest_obs = sorted_obs[-1]

            # Determine trend
            trend_direction, trend_available = self._compute_trend(sorted_obs)

            # Limitations
            limitations = []
            if latest_obs.is_possible_duplicate:
                limitations.append("Flagged as possible duplicate from another report.")
            if latest_obs.verification_status == VerificationStatus.UNVERIFIED:
                limitations.append("Result is unverified by athlete.")

            # Data quality
            quality = "high"
            if latest_obs.is_possible_duplicate or latest_obs.verification_status == VerificationStatus.UNVERIFIED:
                quality = "medium"

            val = latest_obs.normalized_value if latest_obs.normalized_value is not None else latest_obs.numeric_value
            ref_text = latest_obs.laboratory_reference_range.text if latest_obs.laboratory_reference_range else None

            summary = BiomarkerSummary(
                canonical_code=definition.canonical_code,
                canonical_name=definition.canonical_name,
                category=definition.category,
                latest_observation_id=latest_obs.observation_id,
                latest_value=val,
                latest_text_value=latest_obs.text_value,
                inequality_operator=latest_obs.inequality_operator,
                normalized_unit=latest_obs.normalized_unit,
                raw_unit=latest_obs.raw_unit or "",
                laboratory_reference_text=ref_text,
                laboratory_flag=latest_obs.laboratory_flag,
                laboratory_provided_critical_flag=latest_obs.laboratory_provided_critical_flag,
                collected_at=latest_obs.collected_at,
                trend_direction=trend_direction,
                trend_available=trend_available,
                observation_count=len(sorted_obs),
                verification_status=latest_obs.verification_status,
                data_quality=quality,
                limitations=tuple(limitations),
            )
            biomarker_summaries.append(summary)

        # Group BiomarkerSummary by Category
        categories_dict: Dict[BiomarkerCategory, List[BiomarkerSummary]] = {}
        for b_sum in biomarker_summaries:
            categories_dict.setdefault(b_sum.category, []).append(b_sum)

        category_summaries: List[BiomarkerCategorySummary] = []
        # Sort categories deterministically by enum value
        for category in sorted(categories_dict.keys(), key=lambda c: c.value):
            b_list = sorted(categories_dict[category], key=lambda b: b.canonical_code)
            display_name = CATEGORY_DISPLAY_NAMES.get(category, category.value)
            att_cnt = sum(1 for b in b_list if b.laboratory_flag or b.laboratory_provided_critical_flag)

            cat_summary = BiomarkerCategorySummary(
                category=category,
                display_name=display_name,
                biomarkers=tuple(b_list),
                attention_count=att_cnt,
                unresolved_count=0,
            )
            category_summaries.append(cat_summary)

        # Completeness score: simple deterministic ratio of usable resolved observations to all active observations
        usable_cnt = sum(len(b.biomarkers) for b in category_summaries)
        completeness = round(usable_cnt / total_obs_cnt, 4) if total_obs_cnt > 0 else 0.0

        # Status rules
        limitations_global = []
        if unresolved_cnt > 0:
            limitations_global.append(f"{unresolved_cnt} unresolved observation(s) require review.")
        if possible_dup_cnt > 0:
            limitations_global.append(f"{possible_dup_cnt} observation(s) flagged as possible duplicate.")

        if reports_count == 0 or total_obs_cnt == 0 or usable_cnt == 0:
            status = BiomarkersDashboardStatus.UNAVAILABLE
        elif unresolved_cnt > 0 or possible_dup_cnt > 0 or verified_cnt < total_obs_cnt:
            status = BiomarkersDashboardStatus.PARTIAL
        else:
            status = BiomarkersDashboardStatus.READY

        metadata = BiomarkersDashboardMetadata(
            status=status,
            completeness_score=completeness,
            limitations=tuple(limitations_global),
            evidence=(),
            generated_at=now,
            data_as_of=latest_coll_dt,
        )

        date_str = latest_coll_dt.strftime("%Y-%m-%d") if latest_coll_dt else None

        return BiomarkersDashboard(
            contract_version="1.0",
            metadata=metadata,
            total_reports=reports_count,
            active_reports=active_reports_count,
            total_observations=total_obs_cnt,
            verified_observations=verified_cnt,
            unresolved_observations=unresolved_cnt,
            possible_duplicates=possible_dup_cnt,
            latest_collection_date=date_str,
            categories=tuple(category_summaries),
            unresolved_items=tuple(unresolved_items),
            data_quality_summary={
                "completeness_score": completeness,
                "has_unresolved_items": unresolved_cnt > 0,
                "has_possible_duplicates": possible_dup_cnt > 0,
            },
        )

    def _compute_trend(self, obs_list: List[LaboratoryObservation]) -> Tuple[str, bool]:
        """
        Technical deterministic trend computation.
        Requires >= 2 active observations for same canonical_code with numeric values,
        compatible units, and distinct timestamps.
        """
        valid_obs = [
            o for o in obs_list
            if (o.normalized_value is not None or o.numeric_value is not None)
            and o.inequality_operator is None
        ]

        if len(valid_obs) < 2:
            return "unavailable", False

        # Sort by collected_at
        sorted_valid = sorted(valid_obs, key=lambda o: o.collected_at)
        o1 = sorted_valid[-2]
        o2 = sorted_valid[-1]

        if o1.collected_at == o2.collected_at:
            return "unavailable", False

        # Check unit compatibility
        u1 = o1.normalized_unit or o1.raw_unit
        u2 = o2.normalized_unit or o2.raw_unit
        if u1 and u2 and u1.strip().lower() != u2.strip().lower():
            return "unavailable", False

        v1 = o1.normalized_value if o1.normalized_value is not None else o1.numeric_value
        v2 = o2.normalized_value if o2.normalized_value is not None else o2.numeric_value

        if v1 is None or v2 is None:
            return "unavailable", False

        diff = v2 - v1
        if abs(diff) < 1e-4:
            return "stable", True
        elif diff > 1e-4:
            return "increasing", True
        else:
            return "decreasing", True
