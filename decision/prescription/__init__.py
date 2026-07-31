from typing import Any

__all__ = [
    "PrescriptionEngine",
]


def __getattr__(name: str) -> Any:
    if name == "PrescriptionEngine":
        from .engine import PrescriptionEngine

        return PrescriptionEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
