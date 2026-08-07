"""History read models and read providers for TrainingPlan and FinalSessionPrescription."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from training_plan.models import TrainingPlan
from training_plan.prescription import FinalSessionPrescription
from training_plan.repository import (
    FinalSessionPrescriptionRepository,
    TrainingPlanRepository,
    TrainingPlanRepositoryError,
)


@dataclass(frozen=True)
class TrainingPlanHistory:
    """Immutable collection of persisted TrainingPlan records ordered chronologically."""

    records: tuple[TrainingPlan, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise TypeError("records must be tuple")
        seen_ids = set()
        for r in self.records:
            if not isinstance(r, TrainingPlan):
                raise TypeError("records items must be TrainingPlan instances")
            if r.plan_id in seen_ids:
                raise ValueError(f"Duplicate plan_id '{r.plan_id}' in history")
            seen_ids.add(r.plan_id)

    @property
    def count(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class FinalSessionPrescriptionHistory:
    """Immutable collection of persisted FinalSessionPrescription records ordered chronologically."""

    records: tuple[FinalSessionPrescription, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise TypeError("records must be tuple")
        seen_ids = set()
        for r in self.records:
            if not isinstance(r, FinalSessionPrescription):
                raise TypeError("records items must be FinalSessionPrescription instances")
            if r.prescription_id in seen_ids:
                raise ValueError(f"Duplicate prescription_id '{r.prescription_id}' in history")
            seen_ids.add(r.prescription_id)

    @property
    def count(self) -> int:
        return len(self.records)


class TrainingPlanHistoryProviderError(Exception):
    """Infrastructure/source exception for Training Plan history read operations."""


class PrescriptionHistoryProviderError(Exception):
    """Infrastructure/source exception for Prescription history read operations."""


@runtime_checkable
class TrainingPlanHistoryProvider(Protocol):
    """Protocol for reading latest TrainingPlan and plan history."""

    def get_latest_plan(self) -> Optional[TrainingPlan]:
        ...

    def get_plan_history(self) -> TrainingPlanHistory:
        ...


@runtime_checkable
class PrescriptionHistoryProvider(Protocol):
    """Protocol for reading latest FinalSessionPrescription and prescription history."""

    def get_latest_prescription(self) -> Optional[FinalSessionPrescription]:
        ...

    def get_prescription_history(self) -> FinalSessionPrescriptionHistory:
        ...


class RepositoryTrainingPlanHistoryProvider(TrainingPlanHistoryProvider):
    """Read-only history provider backed by TrainingPlanRepository."""

    def __init__(self, repository: TrainingPlanRepository) -> None:
        if repository is None:
            raise TypeError("repository must not be None")
        self._repository = repository

    def get_latest_plan(self) -> Optional[TrainingPlan]:
        try:
            return self._repository.get_latest()
        except TrainingPlanRepositoryError as e:
            raise TrainingPlanHistoryProviderError(f"Failed to retrieve latest TrainingPlan: {e}") from e

    def get_plan_history(self) -> TrainingPlanHistory:
        try:
            records = self._repository.list_records()
            return TrainingPlanHistory(records=records)
        except TrainingPlanRepositoryError as e:
            raise TrainingPlanHistoryProviderError(f"Failed to list TrainingPlan history: {e}") from e


class RepositoryPrescriptionHistoryProvider(PrescriptionHistoryProvider):
    """Read-only history provider backed by FinalSessionPrescriptionRepository."""

    def __init__(self, repository: FinalSessionPrescriptionRepository) -> None:
        if repository is None:
            raise TypeError("repository must not be None")
        self._repository = repository

    def get_latest_prescription(self) -> Optional[FinalSessionPrescription]:
        try:
            return self._repository.get_latest()
        except TrainingPlanRepositoryError as e:
            raise PrescriptionHistoryProviderError(f"Failed to retrieve latest FinalSessionPrescription: {e}") from e

    def get_prescription_history(self) -> FinalSessionPrescriptionHistory:
        try:
            records = self._repository.list_records()
            return FinalSessionPrescriptionHistory(records=records)
        except TrainingPlanRepositoryError as e:
            raise PrescriptionHistoryProviderError(f"Failed to list FinalSessionPrescription history: {e}") from e
