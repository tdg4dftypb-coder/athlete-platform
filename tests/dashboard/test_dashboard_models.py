from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import get_type_hints

import pytest

from dashboard import (
    AthleteDashboard,
    DashboardSection,
    DashboardSectionStatus,
)


def _section() -> DashboardSection:
    return DashboardSection(
        title="Nutrition",
        status=DashboardSectionStatus.PARTIAL,
        confidence=0.5,
        evidence=("nutrition:2026-08-03",),
        limitations=("missing_energy_intake",),
    )


def test_dashboard_section_status_has_the_exact_contract():
    assert tuple(DashboardSectionStatus) == (
        DashboardSectionStatus.READY,
        DashboardSectionStatus.PARTIAL,
        DashboardSectionStatus.UNAVAILABLE,
    )
    assert tuple(status.value for status in DashboardSectionStatus) == (
        "ready",
        "partial",
        "unavailable",
    )


def test_dashboard_section_is_a_frozen_dataclass():
    section = _section()

    assert is_dataclass(DashboardSection)
    assert DashboardSection.__dataclass_params__.frozen is True
    with pytest.raises(FrozenInstanceError):
        section.confidence = 1.0


def test_athlete_dashboard_is_a_frozen_dataclass():
    dashboard = AthleteDashboard(decision=_section())

    assert is_dataclass(AthleteDashboard)
    assert AthleteDashboard.__dataclass_params__.frozen is True
    with pytest.raises(FrozenInstanceError):
        dashboard.decision = None


def test_dashboard_section_has_exact_fields_and_tuple_contracts():
    assert tuple(field.name for field in fields(DashboardSection)) == (
        "title",
        "status",
        "confidence",
        "evidence",
        "limitations",
    )
    type_hints = get_type_hints(DashboardSection)
    assert type_hints == {
        "title": str,
        "status": DashboardSectionStatus,
        "confidence": float,
        "evidence": tuple[str, ...],
        "limitations": tuple[str, ...],
    }


def test_athlete_dashboard_has_exact_optional_section_fields():
    assert tuple(field.name for field in fields(AthleteDashboard)) == (
        "decision",
        "body_composition",
        "nutrition",
        "goal",
        "recommendations",
    )
    assert get_type_hints(AthleteDashboard) == {
        "decision": DashboardSection | None,
        "body_composition": DashboardSection | None,
        "nutrition": DashboardSection | None,
        "goal": DashboardSection | None,
        "recommendations": DashboardSection | None,
    }


def test_dashboard_section_defaults_to_empty_immutable_collections():
    section = DashboardSection(
        title="Decision",
        status=DashboardSectionStatus.READY,
        confidence=1.0,
    )

    assert section.evidence == ()
    assert section.limitations == ()
    assert isinstance(section.evidence, tuple)
    assert isinstance(section.limitations, tuple)


def test_athlete_dashboard_defaults_to_empty_projection():
    assert AthleteDashboard() == AthleteDashboard(
        decision=None,
        body_composition=None,
        nutrition=None,
        goal=None,
        recommendations=None,
    )


def test_models_support_value_equality_repr_and_hashing():
    section = _section()
    equal_section = _section()
    dashboard = AthleteDashboard(nutrition=section)
    equal_dashboard = AthleteDashboard(nutrition=equal_section)

    assert section == equal_section
    assert dashboard == equal_dashboard
    assert "DashboardSection" in repr(section)
    assert "AthleteDashboard" in repr(dashboard)
    assert hash(section) == hash(equal_section)
    assert hash(dashboard) == hash(equal_dashboard)
    assert {section, equal_section} == {section}
    assert {dashboard, equal_dashboard} == {dashboard}


def test_tuple_values_cannot_be_mutated_through_the_models():
    section = _section()

    with pytest.raises(TypeError):
        section.evidence[0] = "changed"
    with pytest.raises(AttributeError):
        section.limitations.append("changed")


def test_dashboard_package_exports_exact_public_models():
    import dashboard
    from dashboard.models import (
        AthleteDashboard as ModelAthleteDashboard,
        DashboardSection as ModelDashboardSection,
        DashboardSectionStatus as ModelDashboardSectionStatus,
    )

    assert dashboard.__all__ == [
        "AthleteDashboard",
        "DashboardEngine",
        "DashboardSection",
        "DashboardSectionStatus",
    ]
    assert dashboard.AthleteDashboard is ModelAthleteDashboard
    assert dashboard.DashboardSection is ModelDashboardSection
    assert dashboard.DashboardSectionStatus is ModelDashboardSectionStatus
