"""Repository protocols and exception contracts for Training Plan Bounded Context."""
from datetime import date
from typing import Protocol, runtime_checkable

from training_plan.models import TrainingPlan
from training_plan.prescription import FinalSessionPrescription


class TrainingPlanRepositoryError(Exception):
    """General infrastructure exception for Training Plan repository operations."""


class TrainingPlanConflictError(TrainingPlanRepositoryError):
    """Raised when attempting to save a plan/prescription with an existing ID but different payload."""


class TrainingPlanDataError(TrainingPlanRepositoryError):
    """Raised when stored payload or metadata is corrupted, inconsistent, or unparseable."""


@runtime_checkable
class TrainingPlanRepository(Protocol):
    """Repository boundary for persisting and retrieving TrainingPlan instances."""

    def save(self, plan: TrainingPlan) -> None:
        """Persists a TrainingPlan append-only. Idempotent for identical payloads."""
        ...

    def get_by_id(self, plan_id: str) -> TrainingPlan | None:
        """Retrieves a single TrainingPlan by plan_id."""
        ...

    def get_latest(self) -> TrainingPlan | None:
        """Retrieves the latest generated TrainingPlan (ordered by generated_at desc, version desc, plan_id desc)."""
        ...

    def get_for_date(self, target_date: date) -> TrainingPlan | None:
        """Retrieves the newest applicable TrainingPlan covering target_date."""
        ...

    def list_records(self) -> tuple[TrainingPlan, ...]:
        """Lists all TrainingPlan instances ordered by generated_at asc, version asc, plan_id asc."""
        ...


@runtime_checkable
class FinalSessionPrescriptionRepository(Protocol):
    """Repository boundary for persisting and retrieving FinalSessionPrescription instances."""

    def save(self, prescription: FinalSessionPrescription) -> None:
        """Persists a FinalSessionPrescription append-only. Idempotent for identical payloads."""
        ...

    def get_by_id(self, prescription_id: str) -> FinalSessionPrescription | None:
        """Retrieves a single FinalSessionPrescription by prescription_id."""
        ...

    def get_latest(self) -> FinalSessionPrescription | None:
        """Retrieves the latest generated FinalSessionPrescription (ordered by generated_at desc, prescription_id desc)."""
        ...

    def list_records(self) -> tuple[FinalSessionPrescription, ...]:
        """Lists all FinalSessionPrescription instances ordered by generated_at asc, prescription_id asc."""
        ...
