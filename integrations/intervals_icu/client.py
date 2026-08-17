"""Small read-only Intervals.icu HTTP client."""
from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from datetime import date
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import AuthenticationFailure, MalformedResponse, ProviderUnavailable, RateLimited
from .models import IntervalsActivity, IntervalsConfiguration


@dataclass(frozen=True)
class TransportResponse:
    status: int
    body: bytes
    headers: dict


class UrllibTransport:
    def get(self, url: str, headers: dict, timeout: float) -> TransportResponse:
        try:
            with urlopen(Request(url, headers=headers, method="GET"), timeout=timeout) as response:
                return TransportResponse(response.status, response.read(), dict(response.headers))
        except HTTPError as error:
            return TransportResponse(error.code, error.read(), dict(error.headers or {}))
        except (URLError, TimeoutError) as error:
            raise ProviderUnavailable("Intervals.icu request failed") from error


class IntervalsClient:
    BASE_URL = "https://intervals.icu/api/v1"

    def __init__(self, configuration: IntervalsConfiguration, transport=None, *, timeout=15.0,
                 max_attempts=3, sleeper=time.sleep):
        self.configuration = configuration.require()
        self.transport = transport or UrllibTransport()
        self.timeout = timeout
        self.max_attempts = max(1, min(max_attempts, 4))
        self.sleeper = sleeper

    def list_activities(self, oldest: date, newest: date) -> tuple[IntervalsActivity, ...]:
        query = urlencode({"oldest": oldest.isoformat(), "newest": newest.isoformat()})
        url = f"{self.BASE_URL}/athlete/{self.configuration.athlete_id}/activities?{query}"
        credential = b64encode(f"API_KEY:{self.configuration.api_key}".encode()).decode()
        headers = {"Authorization": f"Basic {credential}", "Accept": "application/json",
                   "User-Agent": "AthletePlatform/1.0"}
        for attempt in range(self.max_attempts):
            try:
                response = self.transport.get(url, headers, self.timeout)
            except ProviderUnavailable:
                if attempt + 1 == self.max_attempts:
                    raise
                self.sleeper(2 ** attempt)
                continue
            if response.status in (401, 403):
                raise AuthenticationFailure("Intervals.icu authentication failed")
            if response.status == 429:
                if attempt + 1 == self.max_attempts:
                    raise RateLimited("Intervals.icu rate limit exhausted")
                retry_after = response.headers.get("Retry-After", "1")
                try:
                    delay = min(max(float(retry_after), 0.0), 60.0)
                except ValueError:
                    delay = 2 ** attempt
                self.sleeper(delay)
                continue
            if response.status >= 500:
                if attempt + 1 == self.max_attempts:
                    raise ProviderUnavailable("Intervals.icu unavailable")
                self.sleeper(2 ** attempt)
                continue
            if response.status != 200:
                raise ProviderUnavailable(f"Intervals.icu HTTP {response.status}")
            try:
                payload = json.loads(response.body.decode())
            except (UnicodeError, json.JSONDecodeError) as error:
                raise MalformedResponse("Intervals.icu returned malformed JSON") from error
            if not isinstance(payload, list):
                raise MalformedResponse("Intervals.icu activities response must be a list")
            return tuple(IntervalsActivity.from_provider(item) for item in payload)
        raise ProviderUnavailable("Intervals.icu retry budget exhausted")
