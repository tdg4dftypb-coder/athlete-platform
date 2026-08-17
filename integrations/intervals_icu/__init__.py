"""Read-only Intervals.icu activity integration."""

from .client import IntervalsClient
from .models import IntervalsActivity, IntervalsConfiguration, IntervalsSyncResult
from .persistence import IntervalsRepository, IntervalsSchema
from .service import IntervalsSyncService

__all__ = [
    "IntervalsActivity", "IntervalsClient", "IntervalsConfiguration",
    "IntervalsRepository", "IntervalsSchema", "IntervalsSyncResult",
    "IntervalsSyncService",
]
