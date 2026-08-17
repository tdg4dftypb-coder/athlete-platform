"""Authenticated bounded WSGI adapter for HealthKit ingestion."""
from __future__ import annotations

from hmac import compare_digest
import json

from health_ingestion.persistence import HealthKitBatchCollisionError


MAX_BODY_BYTES = 1_000_000


class HealthKitIngestionEndpoint:
    def __init__(self, service, token: str | None) -> None:
        self._service = service
        self._token = token

    def handle(self, environ: dict) -> tuple[str, dict]:
        if not self._token:
            return "503 Service Unavailable", {"error": "healthkit_ingestion_not_configured"}
        supplied = environ.get("HTTP_AUTHORIZATION", "")
        expected = f"Bearer {self._token}"
        if not supplied or not compare_digest(supplied, expected):
            return "401 Unauthorized", {"error": "unauthorized"}
        try:
            length = int(environ.get("CONTENT_LENGTH", "0"))
        except ValueError:
            return "400 Bad Request", {"error": "invalid_content_length"}
        if not 1 <= length <= MAX_BODY_BYTES:
            return "413 Payload Too Large", {"error": "invalid_body_size"}
        try:
            raw = environ["wsgi.input"].read(length)
            payload = json.loads(raw.decode("utf-8"))
            ack = self._service.ingest(payload)
            return "200 OK", ack.to_dict()
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            return "400 Bad Request", {"error": "invalid_healthkit_batch"}
        except HealthKitBatchCollisionError:
            return "409 Conflict", {"error": "batch_identity_collision"}
        except Exception:
            return "503 Service Unavailable", {"error": "healthkit_persistence_unavailable"}
