from typing import Any, Dict, List

from decision.history_v2 import DecisionHistory
from decision.serialization_v2 import DecisionAuditRecordSerializer


class DecisionHistorySerializer:
    """Stateless serializer for DecisionHistory read models into JSON-safe dictionaries."""

    def __init__(self, record_serializer: DecisionAuditRecordSerializer | None = None) -> None:
        self._record_serializer = record_serializer or DecisionAuditRecordSerializer()

    def serialize(self, history: DecisionHistory) -> Dict[str, Any]:
        if not isinstance(history, DecisionHistory):
            raise TypeError("history must be DecisionHistory instance")

        serialized_records: List[Dict[str, Any]] = [
            self._record_serializer.serialize(rec) for rec in history.records
        ]

        return {
            "records": serialized_records,
            "count": len(history.records),
        }
