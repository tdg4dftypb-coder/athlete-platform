from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from morning_briefing.input_models import MorningBriefingInput


class MorningBriefingInputError(Exception):
    """Raised by a provider when the data source is temporarily unavailable."""


@runtime_checkable
class MorningBriefingInputProvider(Protocol):
    """Public contract for supplying MorningBriefingInput to the HTTP endpoint.

    Implementations must not modify domain models.
    They may raise MorningBriefingInputError when the underlying data source
    is temporarily unavailable — the endpoint translates this to HTTP 503.
    """

    def get_input(self) -> MorningBriefingInput:
        ...


class EmptyMorningBriefingInputProvider:
    """Safe default provider returning an empty briefing input.

    Used when no production provider is configured.
    Returns MorningBriefingInput with all optional fields set to None,
    which results in status=UNAVAILABLE with empty sections in the output.
    """

    def __init__(self, now_fn=None) -> None:
        # now_fn is injectable for deterministic tests
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))

    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=self._now_fn(),
            recovery=None,
            training=None,
            biomarkers=None,
        )
