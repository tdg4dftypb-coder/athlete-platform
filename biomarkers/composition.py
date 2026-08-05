"""
Composition Helper for Biomarkers Dashboard Read Model.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from biomarkers.dashboard import BiomarkersDashboardBuilder
from biomarkers.registry import BiomarkerRegistry, create_default_biomarker_registry
from biomarkers.repository import InMemoryLaboratoryRepository
from biomarkers.serialization import BiomarkersDashboardSerializer

# Shared development in-memory repository instance for development HTTP server adapter
_DEV_REPOSITORY = InMemoryLaboratoryRepository()


def get_development_repository() -> InMemoryLaboratoryRepository:
    """Returns the development in-memory repository instance."""
    return _DEV_REPOSITORY


def build_biomarkers_dashboard_use_case(
    repository: Optional[Any] = None,
    biomarker_registry: Optional[BiomarkerRegistry] = None,
    clock: Optional[Callable[[], datetime]] = None,
) -> Dict[str, Any]:
    """
    Composition use case helper:
    LaboratoryRepository -> BiomarkerRegistry -> BiomarkersDashboardBuilder -> BiomarkersDashboardSerializer.
    
    NOTE: Currently uses InMemoryLaboratoryRepository as a development adapter.
    Data persistence in DuckDB will be connected in future pipeline stages.
    """
    repo = repository if repository is not None else get_development_repository()
    registry = biomarker_registry if biomarker_registry is not None else create_default_biomarker_registry()
    now_fn = clock or (lambda: datetime.now(timezone.utc))

    builder = BiomarkersDashboardBuilder(
        repository=repo,
        biomarker_registry=registry,
        clock=now_fn,
    )
    dashboard = builder.build()
    payload = BiomarkersDashboardSerializer.serialize(dashboard)
    return payload
