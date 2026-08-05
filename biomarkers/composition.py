"""
Development Composition Root and Application Context for Biomarkers.
"""

from datetime import datetime, timezone
import os
from typing import Any, Callable, Dict, Optional

from biomarkers.dashboard import BiomarkersDashboardBuilder
from biomarkers.ingestion import (
    LaboratoryIngestionService,
    SyntheticLaboratoryDocumentExtractor,
    SyntheticLaboratoryResultParser,
)
from biomarkers.persistence import DuckDBLaboratoryRepository
from biomarkers.registry import BiomarkerRegistry, create_default_biomarker_registry
from biomarkers.repository import InMemoryLaboratoryRepository, LaboratoryRepository
from biomarkers.serialization import BiomarkersDashboardSerializer
from biomarkers.units import UnitNormalizer, create_default_unit_normalizer


def build_repository_from_env(
    repository_type: Optional[str] = None,
    db_path: Optional[str] = None,
) -> LaboratoryRepository:
    """
    Factory creating a LaboratoryRepository based on explicit parameter or BIOMARKERS_REPOSITORY env var.
    - 'in_memory' (default for testing and lightweight runtime) -> InMemoryLaboratoryRepository
    - 'duckdb' -> DuckDBLaboratoryRepository (persisted to db_path or BIOMARKERS_DB_PATH)
    """
    repo_kind = (repository_type or os.environ.get("BIOMARKERS_REPOSITORY", "in_memory")).strip().lower()
    if repo_kind == "duckdb":
        target_path = db_path or os.environ.get("BIOMARKERS_DB_PATH", "data/database/biomarkers.duckdb")
        return DuckDBLaboratoryRepository(db_path=target_path)
    return InMemoryLaboratoryRepository()


class BiomarkersApplicationContext:
    """
    Development Application Context holding singletons for Biomarkers domain services:
    - repository: LaboratoryRepository (InMemoryLaboratoryRepository or DuckDBLaboratoryRepository)
    - registry: BiomarkerRegistry
    - unit_normalizer: UnitNormalizer
    - ingestion_service: LaboratoryIngestionService
    - clock: provider for aware UTC datetimes
    """

    def __init__(
        self,
        repository: Optional[LaboratoryRepository] = None,
        registry: Optional[BiomarkerRegistry] = None,
        unit_normalizer: Optional[UnitNormalizer] = None,
        clock: Optional[Callable[[], datetime]] = None,
        db_path: Optional[str] = None,
    ) -> None:
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.repository = repository if repository is not None else build_repository_from_env(db_path=db_path)
        self.registry = registry if registry is not None else create_default_biomarker_registry()
        self.unit_normalizer = unit_normalizer if unit_normalizer is not None else create_default_unit_normalizer()
        self.ingestion_service = LaboratoryIngestionService(
            extractor=SyntheticLaboratoryDocumentExtractor(),
            parser=SyntheticLaboratoryResultParser(),
            biomarker_registry=self.registry,
            unit_normalizer=self.unit_normalizer,
            repository=self.repository,
            clock=self.clock,
        )

    def get_dashboard_payload(self) -> Dict[str, Any]:
        """Builds and serializes BiomarkersDashboard payload from current repository state."""
        builder = BiomarkersDashboardBuilder(
            repository=self.repository,
            biomarker_registry=self.registry,
            clock=self.clock,
        )
        dashboard = builder.build()
        return BiomarkersDashboardSerializer.serialize(dashboard)


# Global default development context instance for HTTP server process
_DEFAULT_CONTEXT: Optional[BiomarkersApplicationContext] = None


def get_default_biomarkers_context() -> BiomarkersApplicationContext:
    """Returns the shared process-wide BiomarkersApplicationContext singleton."""
    global _DEFAULT_CONTEXT
    if _DEFAULT_CONTEXT is None:
        _DEFAULT_CONTEXT = BiomarkersApplicationContext()
    return _DEFAULT_CONTEXT


def reset_default_biomarkers_context() -> None:
    """Resets global context singleton for testing."""
    global _DEFAULT_CONTEXT
    _DEFAULT_CONTEXT = None


def build_biomarkers_dashboard_use_case(
    context: Optional[BiomarkersApplicationContext] = None,
    clock: Optional[Callable[[], datetime]] = None,
) -> Dict[str, Any]:
    """
    Composition use case helper.
    Uses BiomarkersApplicationContext to generate BiomarkersDashboardPayloadV1.
    """
    if context is not None:
        ctx = context
    elif clock is not None:
        ctx = BiomarkersApplicationContext(clock=clock)
    else:
        ctx = get_default_biomarkers_context()
    return ctx.get_dashboard_payload()
